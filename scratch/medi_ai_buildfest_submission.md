# MediAI - Infinity AI BuildFest 2026 Submission Draft

## Project Title
MediAI: AI-Powered Medical Triage and Health Assistant for Bangladesh

## Selected Track
Track 3 - Healthcare (HealthTech): AI-Augmented Public Health Systems

## One-Line Summary
I am building MediAI as an AI-powered healthcare assistant that helps people in Bangladesh understand their symptoms, answer guided medical questions, generate a safe triage report, and find suitable doctors or hospitals before visiting a healthcare provider.

## Problem Definition
In Bangladesh, many patients face confusion at the first stage of healthcare. When someone has fever, pain, skin symptoms, breathing problems, pregnancy-related concerns, or other health issues, they often do not know whether the condition is urgent, which specialist they should visit, or which hospital is suitable for them. This problem is stronger in rural and semi-urban areas where doctor availability is limited, waiting time is high, and people often depend on pharmacy advice, relatives, or online misinformation.

Hospitals and clinics also face operational pressure because many patients arrive without structured symptom history, previous documents, or clear department routing. This increases consultation time, creates crowding in outpatient departments, and can delay attention for higher-risk cases.

MediAI addresses this gap by acting as a pre-consultation assistant. It does not replace doctors. Instead, it helps patients organize their symptoms, identify possible risk level, understand whether urgent care may be needed, and prepare a report that can support a faster and more informed consultation.

## Target Users
- General patients in Bangladesh who need early symptom guidance.
- Rural and semi-urban users with limited access to specialist doctors.
- Hospitals, clinics, and diagnostic centers that want better patient intake.
- Telemedicine providers that need structured pre-consultation data.
- Health workers who may need AI-assisted triage support in the future.

## Solution Overview
MediAI provides a web-based health assistant where a user can enter symptoms through a chatbot interface. The system asks follow-up questions, retrieves relevant medical context from a controlled knowledge base, and generates a patient-friendly triage report. The report includes symptom summary, possible risk level, recommended next step, and doctor or hospital guidance.

The platform also supports medical document upload and optional symptom image analysis for visible issues such as rash, wound, swelling, or skin irritation. The image analysis is used only as supportive observation, not as a final diagnosis.

## AI Architecture
The system uses a full-stack AI architecture:

1. Frontend: HTML, CSS, JavaScript, Bootstrap, and Vercel deployment for the user interface, chatbot, dashboard, reports, and doctor recommendation flow.
2. Application Backend: PHP and MySQL for authentication, user records, reports, appointments, medication data, and document uploads.
3. AI Service: FastAPI as a Python AI microservice for question generation, triage report generation, doctor recommendation, document analysis, and image analysis routing.
4. LLM Layer: Groq with Llama 3 for text-based reasoning, follow-up questions, symptom summarization, risk explanation, and report generation.
5. Vision AI Layer: Gemini Vision / Gemini Flash for supportive visual symptom observation from uploaded images.
6. RAG Layer: FAISS-based Vector RAG that retrieves relevant context from local symptom, doctor, and hospital datasets.
7. Workflow Layer: LangGraph to organize the AI flow step by step: symptom input, retrieval, question generation, answer processing, triage reasoning, explanation, and report generation.
8. Deployment and Version Control: Vercel for frontend, Render for backend or AI service deployment, and GitHub for version control and collaboration.

## Type of RAG Used
I currently use FAISS-based Vector RAG. Medical knowledge from CSV datasets such as symptoms, doctors, and hospitals is converted into embeddings and stored in a local vector store. When a user enters symptoms, the system retrieves the most relevant medical context and passes only that context to the LLM. This helps reduce hallucination and makes the AI output more grounded in the selected knowledge base.

In the future, I want to improve this into a GraphRAG-style system by connecting symptoms, conditions, risk factors, specialists, hospitals, and local guidelines as relationships. That would make the reasoning more explainable and closer to healthcare decision pathways.

## AI Usage Details
For text intelligence, I use Groq with Llama 3 to generate follow-up questions, summarize user symptoms, identify risk signals, and create understandable triage reports. I use structured prompts with fixed output formats so the response stays focused, safe, and easy to display in the frontend.

For image support, I use Gemini Vision / Gemini Flash to analyze visible symptoms such as rash, wound, swelling, or irritation. The image output is treated as an observation only and is combined with the user's symptom answers before generating the final report.

For prompt and token optimization, I avoid sending the full conversation history. I send only the user's main symptom, selected answers, retrieved RAG context, and required output format. This keeps the system faster, cheaper, and more controlled.

## MCP Usage
MCP is not directly implemented in the current prototype. The current system uses REST APIs between the frontend, PHP backend, FastAPI AI service, and RAG pipeline.

As a future improvement, I plan to use MCP as an integration layer for connecting the AI assistant with hospital databases, document processing tools, appointment systems, analytics tools, and external medical knowledge services. This would make the platform more modular and production-ready.

## Data Strategy
For the hackathon prototype, I use sample and structured datasets for symptoms, doctors, hospitals, and medical documents. The data is cleaned and organized so it can support retrieval, doctor recommendation, and report generation. User inputs are validated through forms and chatbot flow before being sent to the AI service.

For privacy, I avoid using real patient data in the demo. Any uploaded document or symptom image should be treated as sensitive health information. In production, I would add stronger encryption, role-based access, consent management, data retention policies, audit logs, and compliance alignment with Bangladesh's data protection expectations and healthcare confidentiality practices.

## Quality, Governance, and Observability
For data quality, I check whether symptom, doctor, and hospital records are complete, consistent, and useful for retrieval. I also use structured user inputs to reduce incomplete or vague reports.

For privacy and compliance, I design the prototype around demo or anonymized data and avoid presenting AI output as a confirmed medical diagnosis. In production, I would include stronger patient consent, access control, encrypted storage, and audit trails.

For lineage and observability, I track how a symptom input moves through question generation, RAG retrieval, AI triage, and final report creation. The future version should show which data sources, retrieved context, model calls, and processing steps contributed to the output.

For cost and performance, I optimize model calls by using short prompts, limited context, small retrieval datasets, and efficient API routing. This is important for Bangladesh because healthcare AI must remain affordable for clinics, hospitals, and patients.

## Ethical Safeguards
MediAI is designed as a decision-support system, not a doctor replacement. The system gives guidance, risk awareness, and next-step suggestions, but it does not provide a final diagnosis or prescribe treatment.

The AI output includes safety language for serious symptoms and encourages users to consult qualified doctors. For sensitive cases such as breathing difficulty, severe pain, pregnancy risks, high fever, or red-flag symptoms, the system should recommend urgent medical attention.

I also plan to improve the system with human-in-the-loop review, medical expert validation, stronger bias testing, Bangla language support, and better explainability for every triage result.

## Evaluation and Quality Measures
I evaluate MediAI through medical relevance, RAG quality, safety, performance, and usability.

Medical relevance means the follow-up questions and final report should match the user's symptoms. RAG quality means the retrieved medical context should be relevant and useful. Safety means the system should avoid final diagnosis and should recommend doctor consultation when risk is high. Performance means the system should respond quickly enough for a smooth user experience. Usability means the chatbot, report, and doctor recommendation flow should be simple for Bangladeshi users.

For future validation, I want to compare AI-generated triage outputs with doctor-reviewed sample cases, measure response time improvement, track successful doctor routing, and collect feedback from real users and healthcare professionals.

## Demo Flow
In the demo, I will show a patient entering a symptom such as fever, headache, rash, or abdominal pain. MediAI will generate follow-up questions, collect answers, retrieve relevant medical knowledge, and generate a triage report. If needed, I will also show symptom image upload and doctor recommendation based on specialty and location.

The expected output is a clear report that summarizes the patient's condition, possible risk level, next-step guidance, and recommended healthcare provider category. The report can help both the patient and the doctor start the consultation with better information.

## Business Model and Sustainability
MediAI can become a B2B and B2B2C health-tech platform for Bangladesh. Hospitals, clinics, diagnostic centers, and telemedicine providers can use it as a patient intake and AI triage layer. The platform can also support subscription-based access for clinics, API integration for telemedicine platforms, and premium analytics for healthcare organizations.

For patients, the value is faster guidance and better preparation before visiting a doctor. For healthcare providers, the value is improved intake quality, reduced unnecessary workload, better routing, and more organized patient history. For public health organizations, the future value is anonymized trend analysis and early risk monitoring.

## Scalability Roadmap
The current version is a working hackathon prototype with frontend, backend, AI service, RAG pipeline, and report generation. The next stage is to improve Bangla support, deploy the system on scalable cloud infrastructure, and test it with more realistic healthcare scenarios.

Future improvements include:
- Bangla and English bilingual chatbot.
- Voice input for low-literacy users.
- Offline or low-bandwidth mode for rural healthcare use.
- GraphRAG with WHO/DGHS-aligned medical knowledge.
- Human-in-the-loop doctor review.
- MCP-based integration with hospital systems.
- SMS or WhatsApp-style patient follow-up.
- Better analytics dashboard for clinics and public health teams.
- Security hardening, audit logs, and compliance documentation.

## Impact Metrics
The impact of MediAI can be measured through:
- Reduction in time needed to prepare patient symptom history.
- Improvement in correct department or specialist routing.
- Faster identification of red-flag symptoms.
- Higher patient confidence before consultation.
- Reduced unnecessary hospital visits for low-risk cases.
- Better structured reports for doctors and clinics.
- Increased access to early guidance for rural and semi-urban users.

## Open-Source Tools, Libraries, and Platforms
I used HTML, CSS, JavaScript, and Bootstrap for the frontend. I used PHP and MySQL for backend data handling. I used FastAPI for the AI microservice. I used FAISS for vector-based RAG retrieval. I used LangGraph for AI workflow orchestration. For text AI, I used Groq with Llama 3. For visual symptom support, I used Gemini Vision / Gemini Flash. I used GitHub for version control, Vercel for frontend deployment, and Render for hosting backend or AI services.

## 3-Minute Pitch Script
0:00 - 0:30: Problem
In Bangladesh, many people do not know what to do when symptoms appear. They may delay care, visit the wrong specialist, or depend on informal advice. At the same time, hospitals and clinics receive patients without structured symptom history, which increases pressure and slows down consultation. I am solving this first-step healthcare gap.

0:30 - 1:00: Solution
My solution is MediAI, an AI-powered medical triage and health assistant. It helps users enter symptoms, answer guided questions, upload documents or symptom images, and receive a safe triage report with next-step guidance and doctor recommendation. It is not a doctor replacement; it is a pre-consultation assistant.

1:00 - 2:00: Demo
In the demo, I enter a symptom. The system generates follow-up questions, collects answers, retrieves relevant medical context using FAISS-based RAG, and creates a patient-friendly report. The user can also upload a symptom image for supportive observation, and the platform can recommend suitable doctors or hospitals based on the case.

2:00 - 2:30: AI Approach
For text reasoning, I use Groq with Llama 3. For image-based symptom support, I use Gemini Vision / Gemini Flash. I use FAISS-based Vector RAG to retrieve relevant symptom, doctor, and hospital knowledge. I use LangGraph to manage the workflow from symptom input to retrieval, question generation, triage reasoning, and report generation. The current system uses REST APIs, and MCP is planned as a future integration layer.

2:30 - 3:00: Impact and Next Step
MediAI can help patients get early guidance, help clinics improve patient intake, and support telemedicine providers with structured pre-consultation reports. My next steps are Bangla support, doctor-validated triage logic, low-bandwidth access, GraphRAG with trusted medical guidelines, and real-world pilot testing with clinics in Bangladesh.

## Final Positioning
MediAI is a realistic HealthTech solution for Bangladesh because it focuses on a real pain point: the gap between symptom confusion and formal medical care. The project combines AI, RAG, workflow orchestration, document handling, image support, and doctor recommendation in one practical system. My goal is to build it responsibly, keep doctors in the loop, and make early healthcare guidance more accessible, affordable, and organized.
