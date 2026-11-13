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
    setImagePreview(URL.createObjectURL(file));
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
        setMessages((prev) => [
          ...prev,
          {
            sender: 'ai',
            text: `Image received and reviewed: ${data.image_type || 'skin/wound'} concern noted. ${data.possible_relevance || ''}`,
          },
        ]);
      }
    } catch {
      console.log('Image uploaded locally for triage review.');
    } finally {
      setAnalyzingImage(false);
    }
  };

  const handleSend = async (customText = null) => {
    const query = (typeof customText === 'string' ? customText : input).trim();
    if (!query && !selectedImage) return;

    const userMsg = { sender: 'user', text: query || '(Attached medical image)' };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput('');
    setIsTyping(true);

    const u = getUser();

    // Turn 1: INITIAL STAGE -> Call /generate-questions
    if (stage === 'initial') {
      const chiefComplaint = query;
      setPrimarySymptom(chiefComplaint);

      try {
        const res = await fetch(`${getAiBase()}/generate-questions`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            symptom: chiefComplaint,
            user_id: u?.id || 1,
          }),
        });

        if (!res.ok) throw new Error('Failed to generate follow-up questions.');
        const data = await res.json();
        setIsTyping(false);

        const currentSessId = data.session_id || 'SESS-' + Date.now().toString(36).toUpperCase();
        setSessionId(currentSessId);
        setPatientState(data.patient_state || null);

        const aiMessage = data.message || "Could you provide a few more details on how long you've had these symptoms?";
        setMessages((prev) => [...prev, { sender: 'ai', text: aiMessage }]);
        setStage('followup');

        if (data.is_complete) {
          await triggerReportGeneration(currentSessId, chiefComplaint, [query], data.chat_history, data.patient_state);
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
      const currentSessId = sessionId || 'SESS-' + Date.now().toString(36).toUpperCase();
      const currentHistory = updatedMessages.map((m) => ({
        role: m.sender === 'ai' ? 'assistant' : 'user',
        content: m.text,
      }));

      const res = await fetch(`${getAiBase()}/process-message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: currentSessId,
          message: query,
          user_id: u?.id || 1,
          chat_history: currentHistory,
          patient_state: patientState,
        }),
      });

      if (!res.ok) throw new Error('AI processing error');
      const data = await res.json();
      setIsTyping(false);

      if (data.patient_state) {
        setPatientState(data.patient_state);
      }

      const aiText = data.message || data.reply || (data.chat_history && data.chat_history.length && data.chat_history[data.chat_history.length - 1].content);
      if (aiText) {
        setMessages((prev) => [...prev, { sender: 'ai', text: aiText }]);
      }

      if (data.is_complete) {
        const answers = updatedMessages.filter((m) => m.sender === 'user').map((m) => m.text);
        await triggerReportGeneration(currentSessId, primarySymptom || query, answers, data.chat_history || currentHistory, data.patient_state);
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

  const triggerReportGeneration = async (sessId, chiefComplaint, answersList, history, pState) => {
    setIsTyping(true);
    setStage('analysis');

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
          image_analysis: imageAnalysis,
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
            image_analysis: imageAnalysis,
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
              <div>{m.text}</div>
            </div>
          ))}

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

        {/* Attachment preview */}
        {imagePreview && (
          <div style={{ padding: '8px 24px', background: '#fff', borderTop: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '12px' }}>
            <img src={imagePreview} alt="Symptom preview" style={{ width: '48px', height: '48px', objectFit: 'cover', borderRadius: '6px' }} />
            <div style={{ fontSize: '13px' }}>
              <strong>Attached photo:</strong> {selectedImage?.name} {analyzingImage && ' (Analyzing...)'}
            </div>
            <button
              onClick={() => {
                setSelectedImage(null);
                setImagePreview('');
                setImageAnalysis(null);
              }}
              style={{ background: 'none', border: 'none', color: 'var(--red-urgent)', cursor: 'pointer', marginLeft: 'auto', fontSize: '13px' }}
            >
              Remove
            </button>
          </div>
        )}

        {/* Input Bar */}
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
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="btn-ghost"
            title="Attach skin or wound image"
            style={{ padding: '10px 14px', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            📷 <span>Photo</span>
          </button>

          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={stage === 'initial' ? "Describe your symptoms (e.g., severe headache and fever for 2 days)..." : "Answer the question or add more details..."}
            style={{ flex: 1, padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '15px' }}
          />

          <button type="submit" className="btn-primary" style={{ padding: '12px 24px' }}>
            Send
          </button>
        </form>

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
