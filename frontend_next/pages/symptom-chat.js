import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';
import Layout from '../components/Layout';
import { getUser, getDjangoBase, getAiBase } from '../lib/api';

const QUICK_ANSWERS = [
  'No',
  'Yes',
  'Mild',
  'Moderate',
  'Severe',
  'Getting worse',
  'Improving',
  'Not sure',
];

export default function SymptomChat() {
  const router = useRouter();
  const [messages, setMessages] = useState([
    {
      sender: 'ai',
      text: "Hello! I'm MediSA, your medical triage companion. Please describe your symptoms in as much detail as you can — what you're feeling, when it started, and how severe it feels. You can also attach an image if you have a visible skin condition or wound.",
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [stage, setStage] = useState('initial'); // initial | followup | analysis | done
  const [sessionId, setSessionId] = useState('');
  const [primarySymptom, setPrimarySymptom] = useState('');
  const [patientState, setPatientState] = useState(null);
  const [selectedImage, setSelectedImage] = useState(null);
  const [imagePreview, setImagePreview] = useState('');
  const [imageAnalysis, setImageAnalysis] = useState(null);
  const [savedImageAnalysis, setSavedImageAnalysis] = useState(null);
  const [savedImagePreview, setSavedImagePreview] = useState('');
  const [analyzingImage, setAnalyzingImage] = useState(false);
  const [report, setReport] = useState(null);
  const [showReportPanel, setShowReportPanel] = useState(false);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleImageChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setSelectedImage(file);
    const previewUrl = URL.createObjectURL(file);
    setImagePreview(previewUrl);
    setAnalyzingImage(true);

    try {
      const fd = new FormData();
      fd.append('file', file);

      const res = await fetch(`${getAiBase()}/analyze-symptom-image-for-triage`, {
        method: 'POST',
        body: fd,
      });

      if (res.ok) {
        const data = await res.json();
        setImageAnalysis(data);
        if (data.image_path) {
          setSavedImagePreview(data.image_path);
        }
      }
    } catch {
      console.log('Image uploaded locally for triage review.');
    } finally {
      setAnalyzingImage(false);
    }
  };

  const handleSend = async (customText = null) => {
    if (analyzingImage || isTyping) return;

    const query = (typeof customText === 'string' ? customText : input).trim();
    if (!query && !selectedImage && !imagePreview) return;

    const currentImage = imagePreview;
    const currentAnalysis = imageAnalysis;
    const serverImgPath = currentAnalysis?.image_path || savedImageAnalysis?.image_path || currentImage;

    // Option A: If user uploaded an image WITHOUT typing text, check clinical relevance
    if (!query && currentImage) {
      const imgType = currentAnalysis?.image_type?.toLowerCase() || '';
      const isNonClinical = !currentAnalysis || imgType === 'other' || imgType === 'unclear';

      if (isNonClinical) {
        // Acknowledge non-clinical photo with a polite clarification, stay in initial stage
        const userMsg = {
          sender: 'user',
          text: 'Attached photo for clinical inspection',
          image: currentImage,
        };
        const aiClarification = {
          sender: 'ai',
          text: "I've reviewed your attached photo, but it does not appear to show an identifiable skin lesion, rash, or localized wound. Could you please describe what symptoms you are experiencing, or upload a clear, focused photo of the affected area?",
          visionAnalysis: currentAnalysis || null,
        };
        setMessages((prev) => [...prev, userMsg, aiClarification]);
        setInput('');
        setSelectedImage(null);
        setImagePreview('');
        setImageAnalysis(null);
        if (fileInputRef.current) fileInputRef.current.value = '';
        return;
      }
    }

    // Determine chief complaint cleanly - never fallback to ambiguous 'Visual symptom presentation'
    const chiefComplaint = query || (
      currentAnalysis?.image_type && currentAnalysis.image_type !== 'other' && currentAnalysis.image_type !== 'unclear'
        ? `Observed ${currentAnalysis.image_type} on uploaded medical photo`
        : 'Symptom Consultation'
    );

    if (currentAnalysis) setSavedImageAnalysis(currentAnalysis);
    if (serverImgPath) setSavedImagePreview(serverImgPath);

    const userMsg = {
      sender: 'user',
      text: query || (currentImage ? 'Attached medical photo for visual inspection' : ''),
      image: currentImage || null,
    };
    const updatedMessages = [...messages, userMsg];

    if (currentAnalysis) {
      updatedMessages.push({
        sender: 'ai',
        text: currentAnalysis.image_type === 'other'
          ? "I've reviewed the uploaded image. " + (currentAnalysis.possible_relevance || "It does not appear to show typical clinical symptoms.")
          : `I've analyzed your attached photo with Gemini Vision. I noted observations for ${currentAnalysis.image_type || 'skin/wound condition'}:`,
        visionAnalysis: currentAnalysis,
      });
    }

    setMessages(updatedMessages);
    setInput('');
    setSelectedImage(null);
    setImagePreview('');
    setImageAnalysis(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    setIsTyping(true);

    const u = getUser();
    const currentSessId = sessionId || 'SESS-' + Date.now().toString(36).toUpperCase();
    if (!sessionId) setSessionId(currentSessId);

    // Format chat history for API
    const currentHistory = updatedMessages.map((m) => ({
      role: m.sender === 'ai' ? 'assistant' : 'user',
      content: m.text,
    }));
    const activeAnalysis = currentAnalysis || savedImageAnalysis;

    // Turn 1: INITIAL STAGE -> Call /generate-questions
    if (stage === 'initial') {
      setPrimarySymptom(chiefComplaint);

      try {
        const res = await fetch(`${getAiBase()}/generate-questions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: currentSessId,
            symptom: chiefComplaint,
            user_id: u?.id || 1,
            chat_history: currentHistory,
            image_analysis: activeAnalysis,
          }),
        });

        if (!res.ok) throw new Error('Failed to generate follow-up questions.');
        const data = await res.json();
        setIsTyping(false);

        if (data.session_id) setSessionId(data.session_id);
        if (data.patient_state) setPatientState(data.patient_state);

        if (data.is_complete) {
          const aiClosing = data.message || "Thank you for providing those details. Generating your triage summary...";
          setMessages((prev) => [...prev, { sender: 'ai', text: aiClosing }]);
          await triggerReportGeneration(currentSessId, chiefComplaint, [chiefComplaint], data.chat_history || currentHistory, data.patient_state, activeAnalysis);
        } else {
          const aiMessage = data.message || "Could you provide a few more details on how long you've had these symptoms?";
          setMessages((prev) => [...prev, { sender: 'ai', text: aiMessage }]);
          setStage('followup');
        }
      } catch (err) {
        setIsTyping(false);
        setStage('followup');
        setMessages((prev) => [
          ...prev,
          {
            sender: 'ai',
            text: "Thank you for explaining your symptoms. Do you also have a high fever, shortness of breath, neck stiffness, or severe pain?",
          },
        ]);
      }
      return;
    }

    // Turn 2+: FOLLOWUP STAGE -> Call /process-message
    try {
      const res = await fetch(`${getAiBase()}/process-message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: currentSessId,
          message: query,
          user_id: u?.id || 1,
          chat_history: currentHistory,
          patient_state: patientState,
          image_analysis: activeAnalysis,
        }),
      });

      if (!res.ok) throw new Error('AI processing error');
      const data = await res.json();
      setIsTyping(false);

      if (data.patient_state) {
        setPatientState(data.patient_state);
      }

      if (data.is_complete) {
        const aiClosing = data.message || "Thank you. I have sufficient clinical details to prepare your triage assessment.";
        setMessages((prev) => [...prev, { sender: 'ai', text: aiClosing }]);
        const answers = updatedMessages.filter((m) => m.sender === 'user').map((m) => m.text);
        await triggerReportGeneration(currentSessId, primarySymptom || query, answers, data.chat_history || currentHistory, data.patient_state, activeAnalysis);
      } else {
        const aiText = data.message || data.reply || (data.chat_history && data.chat_history.length && data.chat_history[data.chat_history.length - 1].content);
        if (aiText) {
          setMessages((prev) => [...prev, { sender: 'ai', text: aiText }]);
        }
      }
    } catch (err) {
      setIsTyping(false);
      setMessages((prev) => [
        ...prev,
        {
          sender: 'ai',
          text: "I've noted that. Are there any other symptoms or preexisting medical conditions I should be aware of?",
        },
      ]);
    }
  };

  const triggerReportGeneration = async (sessId, chiefComplaint, answersList, history, pState, imgAnalysis = null) => {
    setIsTyping(true);
    setStage('analysis');

    const activeImageAnalysis = imgAnalysis || imageAnalysis || savedImageAnalysis;

    const u = getUser();
    try {
      const res = await fetch(`${getAiBase()}/generate-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessId || sessionId,
          symptom: chiefComplaint || primarySymptom || 'Symptom Consultation',
          answers: answersList || messages.filter((m) => m.sender === 'user').map((m) => m.text),
          chat_history: history || messages.map((m) => ({ role: m.sender === 'ai' ? 'assistant' : 'user', content: m.text })),
          user_id: u?.id || 1,
          image_analysis: activeImageAnalysis,
          patient_state: pState || patientState,
        }),
      });

      if (!res.ok) throw new Error('Report generation error');
      const data = await res.json();
      const finalReport = data.report || data;

      setReport(finalReport);
      setShowReportPanel(true);
      setStage('done');

      // Persist to Django
      try {
        await fetch(`${getDjangoBase()}/reports`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: u?.id || 1,
            session_id: sessId || sessionId,
            possible_condition: finalReport.possible_condition || 'Clinical Review Recommended',
            urgency: finalReport.urgency || 'medium',
            recommended_specialist: finalReport.recommended_specialist || 'Medicine Specialist',
            reasoning: finalReport.reasoning || '',
            guidance: finalReport.guidance || '',
            explanation: finalReport.explanation || '',
            symptoms_listed: finalReport.symptoms_listed || [chiefComplaint],
            image_analysis: activeImageAnalysis,
            image_path: activeImageAnalysis?.image_path || (savedImagePreview && !savedImagePreview.startsWith('blob:') ? savedImagePreview : null),
          }),
        });
      } catch (saveErr) {
        console.error('Failed to save triage report in Django:', saveErr);
      }
    } catch {
      // Empathic fallback report
      const fallbackReport = {
        possible_condition: 'Acute Symptom Presentation / Probable Viral Syndrome',
        urgency: 'medium',
        recommended_specialist: 'Medicine Specialist',
        reasoning: `Analysis of reported clinical inputs (${chiefComplaint}) indicates standard symptomatic presentation requiring routine medical consultation.`,
        guidance: 'Maintain adequate hydration, monitor temperature, and rest. Avoid self-medicating without clinical guidance.',
        explanation: 'Clinical decision-support generated through MediSA evidence protocols.',
        symptoms_listed: [chiefComplaint],
      };
      setReport(fallbackReport);
      setShowReportPanel(true);
      setStage('done');
    } finally {
      setIsTyping(false);
    }
  };

  const handleManualComplete = () => {
    const answers = messages.filter((m) => m.sender === 'user').map((m) => m.text);
    triggerReportGeneration(sessionId, primarySymptom || answers[0] || 'Symptoms', answers, null, patientState);
  };

  const getStageLabel = () => {
    switch (stage) {
      case 'initial':
        return 'Describe your symptoms';
      case 'followup':
        return 'Interactive clinical Q&A';
      case 'analysis':
        return 'Analyzing medical evidence...';
      case 'done':
        return 'Triage report ready';
      default:
        return 'Triage assessment';
    }
  };

  return (
    <Layout activePage="symptom-chat">
      <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 100px)' }}>
        {/* Top session bar */}
        <div style={{ background: '#fff', borderBottom: '1px solid var(--border)', padding: '12px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '13px', color: 'var(--ink-muted)', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <strong>Symptom Assessment</strong>
            <span style={{ opacity: 0.6 }}>{sessionId ? `#${sessionId}` : '–'}</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontWeight: 600, color: 'var(--ink)' }}>Stage:</span>
            <span>{getStageLabel()}</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginLeft: '6px' }}>
              <span className={`stage-dot ${['initial', 'followup', 'analysis', 'done'].indexOf(stage) >= 0 ? 'done' : ''}`} />
              <span className={`stage-dot ${['followup', 'analysis', 'done'].indexOf(stage) >= 0 ? 'done' : ''}`} />
              <span className={`stage-dot ${['analysis', 'done'].indexOf(stage) >= 0 ? 'done' : ''}`} />
              <span className={`stage-dot ${stage === 'done' ? 'done active' : ''}`} />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '8px' }}>
            {stage === 'followup' && (
              <button
                onClick={handleManualComplete}
                className="btn-ghost"
                style={{ padding: '4px 12px', fontSize: '12px', borderColor: 'var(--teal)' }}
              >
                Generate Report Now ➔
              </button>
            )}
            {report && (
              <button
                onClick={() => setShowReportPanel(true)}
                className="btn-primary"
                style={{ padding: '4px 12px', fontSize: '12px' }}
              >
                View Report
              </button>
            )}
          </div>
        </div>

        {/* Chat message history */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {messages.map((m, idx) => (
            <div key={idx} className={m.sender === 'ai' ? 'msg msg-ai' : 'msg msg-user'}>
              {m.sender === 'ai' && <div className="msg-label">MediSA AI</div>}
              {m.image && (
                <div style={{ marginBottom: m.text ? '8px' : '0' }}>
                  <img
                    src={m.image}
                    alt="Symptom upload"
                    style={{
                      maxWidth: '240px',
                      maxHeight: '200px',
                      borderRadius: '10px',
                      objectFit: 'cover',
                      display: 'block',
                      border: m.sender === 'user' ? '2px solid rgba(255,255,255,0.7)' : '1px solid #cbd5e1',
                      boxShadow: '0 4px 10px rgba(0,0,0,0.1)',
                      cursor: 'pointer',
                    }}
                    onClick={() => window.open(m.image, '_blank')}
                    title="Click to view full image"
                  />
                </div>
              )}
              {m.text && <div style={{ wordBreak: 'break-word' }}>{m.text}</div>}
              {m.visionAnalysis && (
                <div
                  style={{
                    marginTop: '10px',
                    padding: '12px 14px',
                    borderRadius: '10px',
                    background: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    fontSize: '13px',
                    color: '#1e293b',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontWeight: 600, color: '#0f766e', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      👁️ Gemini Vision Findings
                    </span>
                    <span
                      style={{
                        padding: '2px 8px',
                        borderRadius: '12px',
                        fontSize: '11px',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                        background:
                          m.visionAnalysis.assessment_flag === 'red'
                            ? '#fee2e2'
                            : m.visionAnalysis.assessment_flag === 'yellow'
                            ? '#fef3c7'
                            : '#dcfce7',
                        color:
                          m.visionAnalysis.assessment_flag === 'red'
                            ? '#dc2626'
                            : m.visionAnalysis.assessment_flag === 'yellow'
                            ? '#d97706'
                            : '#16a34a',
                      }}
                    >
                      {m.visionAnalysis.assessment_flag === 'red'
                        ? '⚠️ Urgent Attention'
                        : m.visionAnalysis.assessment_flag === 'yellow'
                        ? '⚡ Clinical Review Recommended'
                        : '✓ Low Concern'}
                    </span>
                  </div>

                  {m.visionAnalysis.image_type && (
                    <div style={{ marginBottom: '6px', color: '#475569' }}>
                      <strong>Identified Area/Type:</strong>{' '}
                      <span style={{ textTransform: 'capitalize' }}>{m.visionAnalysis.image_type}</span>
                      {m.visionAnalysis.confidence && ` • Confidence: ${m.visionAnalysis.confidence}`}
                    </div>
                  )}

                  {m.visionAnalysis.visible_observations?.length > 0 && (
                    <div style={{ marginBottom: '6px' }}>
                      <strong style={{ color: '#334155' }}>Visual Observations:</strong>
                      <ul style={{ margin: '4px 0 0 16px', padding: 0, color: '#475569' }}>
                        {m.visionAnalysis.visible_observations.map((obs, i) => (
                          <li key={i}>{obs}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {m.visionAnalysis.possible_relevance && (
                    <div style={{ fontSize: '12px', color: '#64748b', fontStyle: 'italic', marginTop: '6px' }}>
                      {m.visionAnalysis.possible_relevance}
                    </div>
                  )}

                  {m.visionAnalysis.red_flags?.length > 0 && (
                    <div
                      style={{
                        marginTop: '8px',
                        padding: '6px 10px',
                        borderRadius: '6px',
                        background: '#fef2f2',
                        border: '1px solid #fecaca',
                        fontSize: '12px',
                        color: '#b91c1c',
                        fontWeight: 500,
                      }}
                    >
                      🚨 Red Flags: {m.visionAnalysis.red_flags.join(', ')}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {/* In-chat Assessment Summary Card when complete */}
          {stage === 'done' && report && (
            <div
              style={{
                margin: '12px 0',
                padding: '16px 20px',
                background: '#f0fdfa',
                border: '1px solid #99f6e4',
                borderRadius: '12px',
                maxWidth: '680px',
                boxShadow: '0 2px 8px rgba(15, 118, 110, 0.08)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontWeight: 600, color: '#0f766e', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>📋</span> Assessment Summary Ready
                </span>
                <span
                  style={{
                    padding: '3px 10px',
                    borderRadius: '12px',
                    fontSize: '11px',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    background: report.urgency === 'high' ? '#fee2e2' : report.urgency === 'medium' ? '#fef3c7' : '#dcfce7',
                    color: report.urgency === 'high' ? '#dc2626' : report.urgency === 'medium' ? '#d97706' : '#16a34a',
                  }}
                >
                  {report.urgency || 'Routine'} Urgency
                </span>
              </div>
              <div style={{ fontSize: '13px', color: '#1e293b', marginBottom: '6px' }}>
                <strong>Suspected Condition:</strong> {report.possible_condition || 'Clinical Review Recommended'}
              </div>
              <div style={{ fontSize: '12px', color: '#475569', marginBottom: '12px' }}>
                <strong>Recommended Specialist:</strong> {report.recommended_specialist || 'General Medicine'}
              </div>
              <button
                type="button"
                onClick={() => setShowReportPanel(true)}
                className="btn-primary"
                style={{ padding: '8px 16px', fontSize: '13px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                <span>📄</span> Open Full Triage Report
              </button>
            </div>
          )}

          {isTyping && (
            <div className="msg-typing">
              <div className="typing-dots">
                <span /><span /><span />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Interactive Quick Answer Chips */}
        {stage === 'followup' && (
          <div style={{ padding: '8px 24px', background: '#fdfbf7', borderTop: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '12px', color: 'var(--ink-muted)', fontWeight: 600 }}>Quick reply:</span>
            {QUICK_ANSWERS.map((ans) => (
              <button
                key={ans}
                type="button"
                onClick={() => handleSend(ans)}
                className="btn-ghost"
                style={{ padding: '4px 10px', fontSize: '12px', borderRadius: '16px', background: '#fff' }}
              >
                {ans}
              </button>
            ))}
          </div>
        )}

        {/* Attachment preview bar */}
        {imagePreview && (
          <div
            style={{
              padding: '10px 24px',
              background: '#f8fafc',
              borderTop: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
            }}
          >
            <div style={{ position: 'relative' }}>
              <img
                src={imagePreview}
                alt="Symptom preview"
                style={{
                  width: '52px',
                  height: '52px',
                  objectFit: 'cover',
                  borderRadius: '8px',
                  border: '1px solid #cbd5e1',
                  boxShadow: '0 2px 6px rgba(0,0,0,0.06)',
                }}
              />
              {analyzingImage && (
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    background: 'rgba(0,0,0,0.45)',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#fff',
                    fontSize: '12px',
                  }}
                >
                  ⏳
                </div>
              )}
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: '13px',
                  fontWeight: 600,
                  color: 'var(--ink)',
                  textOverflow: 'ellipsis',
                  overflow: 'hidden',
                  whiteSpace: 'nowrap',
                }}
              >
                {selectedImage?.name || 'Attached Symptom Photo'}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--ink-muted)', marginTop: '2px' }}>
                {analyzingImage ? (
                  <span style={{ color: 'var(--teal)', fontWeight: 500 }}>
                    🔍 Analyzing with Gemini Vision...
                  </span>
                ) : imageAnalysis?.image_type === 'other' || imageAnalysis?.image_type === 'unclear' ? (
                  <span style={{ color: '#d97706', fontWeight: 500 }}>
                    ⚠️ Non-clinical image detected — please describe your symptoms
                  </span>
                ) : imageAnalysis ? (
                  <span style={{ color: '#16a34a', fontWeight: 500 }}>
                    ✓ Gemini Vision Ready ({imageAnalysis.image_type || 'reviewed'})
                  </span>
                ) : (
                  <span>Ready to attach</span>
                )}
              </div>
            </div>

            <button
              type="button"
              onClick={() => {
                setSelectedImage(null);
                setImagePreview('');
                setImageAnalysis(null);
                if (fileInputRef.current) fileInputRef.current.value = '';
              }}
              style={{
                padding: '6px 12px',
                color: 'var(--red-urgent)',
                fontSize: '13px',
                borderRadius: '6px',
                border: '1px solid #fecaca',
                background: '#fff',
                cursor: 'pointer',
              }}
            >
              Remove
            </button>
          </div>
        )}

        {/* Input Bar or Completion Banner */}
        {stage === 'done' ? (
          <div
            style={{
              padding: '16px 24px',
              background: '#f8fafc',
              borderTop: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '16px',
              flexWrap: 'wrap',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  background: '#dcfce7',
                  color: '#16a34a',
                  fontWeight: 'bold',
                  fontSize: '15px',
                }}
              >
                ✓
              </span>
              <div>
                <div style={{ fontWeight: 600, fontSize: '14px', color: 'var(--ink)' }}>
                  Triage Consultation Complete
                </div>
                <div style={{ fontSize: '12px', color: 'var(--ink-muted)' }}>
                  {report?.possible_condition ? `Summary ready: ${report.possible_condition}` : 'Clinical summary generated'}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <button
                type="button"
                onClick={() => setShowReportPanel(true)}
                className="btn-primary"
                style={{
                  padding: '10px 18px',
                  fontSize: '13px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <span>📄</span> View Full Triage Report
              </button>

              <button
                type="button"
                onClick={() => {
                  setStage('initial');
                  setMessages([
                    {
                      sender: 'ai',
                      text: "Hello! I'm MediSA, your medical triage companion. Please describe your symptoms in as much detail as you can — what you're feeling, when it started, and how severe it feels. You can also attach an image if you have a visible skin condition or wound.",
                    },
                  ]);
                  setReport(null);
                  setShowReportPanel(false);
                  setPatientState(null);
                  setSavedImageAnalysis(null);
                  setSavedImagePreview('');
                  setSessionId('SESS-' + Date.now().toString(36).toUpperCase());
                }}
                className="btn-ghost"
                style={{
                  padding: '10px 14px',
                  fontSize: '13px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <span>🔄</span> Start New Consultation
              </button>
            </div>
          </div>
        ) : (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            style={{ padding: '16px 24px', background: '#fff', borderTop: '1px solid var(--border)', display: 'flex', gap: '12px', alignItems: 'center' }}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleImageChange}
              accept="image/*"
              style={{ display: 'none' }}
              disabled={analyzingImage || isTyping}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="btn-ghost"
              title="Attach skin or wound image"
              disabled={analyzingImage || isTyping}
              style={{
                padding: '10px 14px',
                fontSize: '14px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                border: imagePreview ? '1px solid var(--teal)' : '1px solid var(--border)',
                background: imagePreview ? 'var(--teal-light)' : '#fff',
                color: imagePreview ? 'var(--teal)' : 'inherit',
                borderRadius: '8px',
                cursor: (analyzingImage || isTyping) ? 'not-allowed' : 'pointer',
                opacity: (analyzingImage || isTyping) ? 0.6 : 1,
                transition: 'all 0.2s ease',
              }}
            >
              📷 <span style={{ fontWeight: 500 }}>{imagePreview ? 'Photo Ready' : 'Photo'}</span>
            </button>

            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isTyping}
              placeholder={stage === 'initial' ? "Describe your symptoms (e.g., severe headache and fever for 2 days)..." : "Answer the question or add more details..."}
              style={{ flex: 1, padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '15px' }}
            />

            <button
              type="submit"
              className="btn-primary"
              style={{
                padding: '12px 24px',
                opacity: (analyzingImage || isTyping || (!input.trim() && !imagePreview)) ? 0.6 : 1,
                cursor: (analyzingImage || isTyping || (!input.trim() && !imagePreview)) ? 'not-allowed' : 'pointer',
              }}
              disabled={analyzingImage || isTyping || (!input.trim() && !imagePreview)}
            >
              {analyzingImage ? 'Analyzing...' : isTyping ? 'Thinking...' : 'Send'}
            </button>
          </form>
        )}

        {/* Slide-out Report Drawer */}
        {showReportPanel && report && (
          <div
            style={{
              position: 'fixed',
              top: 0,
              right: 0,
              bottom: 0,
              width: '460px',
              maxWidth: '92vw',
              background: '#fff',
              boxShadow: 'var(--shadow-lg)',
              borderLeft: '1px solid var(--border)',
              zIndex: 300,
              display: 'flex',
              flexDirection: 'column',
              padding: '24px',
              overflowY: 'auto',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ fontSize: '20px', margin: 0 }}>Triage Assessment Report</h2>
              <button
                onClick={() => setShowReportPanel(false)}
                style={{ background: 'none', border: 'none', fontSize: '24px', cursor: 'pointer', color: 'var(--ink-muted)' }}
              >
                ✕
              </button>
            </div>

            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '13px', color: 'var(--ink-muted)', marginBottom: '4px' }}>Inferred Condition</div>
              <div style={{ fontSize: '20px', fontWeight: 600, color: 'var(--ink)' }}>
                {report.possible_condition}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
              <span className={`badge badge-${report.urgency || 'medium'}`} style={{ textTransform: 'uppercase' }}>
                Urgency: {report.urgency || 'medium'}
              </span>
              {report.recommended_specialist && (
                <span className="badge badge-low" style={{ background: 'var(--teal-light)', color: 'var(--teal)' }}>
                  {report.recommended_specialist}
                </span>
              )}
            </div>

            {/* Visual Assessment from Image (if attached) */}
            {savedImageAnalysis && (
              <div
                style={{
                  marginBottom: '18px',
                  background: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: '10px',
                  padding: '14px',
                }}
              >
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--ink)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span>📷</span> Visual Inspection Findings
                </div>
                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                  {savedImagePreview && (
                    <img
                      src={savedImagePreview}
                      alt="Uploaded symptom"
                      style={{
                        width: '68px',
                        height: '68px',
                        borderRadius: '8px',
                        objectFit: 'cover',
                        border: '1px solid #cbd5e1',
                        cursor: 'pointer',
                      }}
                      onClick={() => window.open(savedImagePreview, '_blank')}
                      title="Click to view full image"
                    />
                  )}
                  <div style={{ fontSize: '12px', flex: 1 }}>
                    <div><strong>Type:</strong> <span style={{ textTransform: 'capitalize' }}>{savedImageAnalysis.image_type}</span></div>
                    {savedImageAnalysis.confidence && <div><strong>Confidence:</strong> {savedImageAnalysis.confidence}</div>}
                    {savedImageAnalysis.visible_observations?.length > 0 && (
                      <div style={{ marginTop: '4px', color: '#475569' }}>
                        {savedImageAnalysis.visible_observations.join(' • ')}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {report.reasoning && (
              <div className="report-section" style={{ marginBottom: '16px' }}>
                <h4 style={{ fontSize: '14px', marginBottom: '6px' }}>Clinical Reasoning</h4>
                <p style={{ fontSize: '14px', color: 'var(--ink-muted)' }}>{report.reasoning}</p>
              </div>
            )}

            {report.guidance && (
              <div className="report-section" style={{ marginBottom: '16px' }}>
                <h4 style={{ fontSize: '14px', marginBottom: '6px' }}>Guidance & Home Care</h4>
                <p style={{ fontSize: '14px', color: 'var(--ink-muted)' }}>{report.guidance}</p>
              </div>
            )}

            {report.explanation && (
              <div className="report-section" style={{ marginBottom: '16px' }}>
                <h4 style={{ fontSize: '14px', marginBottom: '6px' }}>Diagnostic Explanation</h4>
                <p style={{ fontSize: '14px', color: 'var(--ink-muted)' }}>{report.explanation}</p>
              </div>
            )}

            <div style={{ marginTop: 'auto', paddingTop: '20px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <button
                onClick={() => {
                  router.push(
                    `/doctors?condition=${encodeURIComponent(report.possible_condition || '')}&specialization=${encodeURIComponent(report.recommended_specialist || '')}&symptom=${encodeURIComponent(primarySymptom || '')}`
                  );
                }}
                className="btn-primary"
                style={{ width: '100%', textAlign: 'center', padding: '12px' }}
              >
                Find & Book Specialist from Directory →
              </button>
              <button
                onClick={() => setShowReportPanel(false)}
                className="btn-ghost"
                style={{ width: '100%', textAlign: 'center' }}
              >
                Close Report
              </button>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
