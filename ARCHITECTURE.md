# Image Upload Architecture Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Web Browser)                    │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Symptom Chat Interface (HTML/CSS)             │  │
│  │                                                              │  │
│  │  ┌─────────────────────────────────────────────────────┐   │  │
│  │  │ Chat Messages Display                              │   │  │
│  │  └─────────────────────────────────────────────────────┘   │  │
│  │                          ▲                                  │  │
│  │                          │ displayReportReady()            │  │
│  │                          │                                  │  │
│  │  ┌─────────────────────────────────────────────────────┐   │  │
│  │  │ Image Upload Button & Preview                       │   │  │
│  │  │ • handleImageSelection()                             │   │  │
│  │  │ • clearSelectedImage()                               │   │  │
│  │  │ • analyzeSymptomImage()                              │   │  │
│  │  └─────────────────────────────────────────────────────┘   │  │
│  │                                                              │  │
│  │  ┌─────────────────────────────────────────────────────┐   │  │
│  │  │ Chat Input & Send                                   │   │  │
│  │  │ • sendMessage()                                      │   │  │
│  │  │ • generateReportWithImage()                          │   │  │
│  │  └─────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  JavaScript State:                                               │
│  • selectedImageFile                                             │
│  • imageAnalysis                                                 │
│  • sessionId, primarySymptom, followupAnswers                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/JSON
                              │
        ┌─────────────────────┴──────────────────────┐
        │                                             │
        ▼                                             ▼
┌──────────────────────────────┐        ┌──────────────────────────────┐
│   FastAPI Server (Python)     │        │    PHP Backend (MySQL)       │
│   Port: 8000                  │        │    Endpoints: /api/*.php     │
│                               │        │                              │
│ NEW ROUTES:                   │        │ UPDATED TABLES:              │
│ ┌───────────────────────────┐ │        │ ┌──────────────────────────┐ │
│ │ POST /analyze-symptom-    │ │        │ │ triage_reports table:    │ │
│ │ image-for-triage          │ │        │ │ + image_analysis column  │ │
│ │                           │ │        │ │   (LONGTEXT JSON)        │ │
│ │ Accepts: File upload      │ │        │ │                          │ │
│ │ Returns: {                │ │        │ │ ENDPOINTS:               │ │
│ │   image_type,             │ │        │ │ • GET /api/reports.php   │ │
│ │   visible_observations,   │ │        │ │ • POST /api/reports.php  │ │
│ │   red_flags,              │ │        │ │ • PUT /api/reports.php   │ │
│ │   confidence,             │ │        │ │   (NEW)                  │ │
│ │   assessment_flag         │ │        │ │                          │ │
│ │ }                         │ │        │ │ Functions:               │ │
│ └───────────────────────────┘ │        │ │ • decodeReportData()     │ │
│                               │        │ │ • Store/retrieve         │ │
│ ENHANCED ROUTES:              │        │ │   image_analysis         │ │
│ ┌───────────────────────────┐ │        │ └──────────────────────────┘ │
│ │ POST /generate-report     │ │        └──────────────────────────────┘
│ │                           │ │
│ │ Enhanced to accept:       │ │
│ │ • image_analysis (opt)    │ │
│ │                           │ │
│ │ Calls: run_report_        │ │
│ │ generation()              │ │
│ └───────────────────────────┘ │
│                               │
│ WORKFLOW (workflow.py):       │
│ ┌───────────────────────────┐ │
│ │ TriageState:              │ │
│ │ + image_analysis: dict    │ │
│ │                           │ │
│ │ node_triage_engine():     │ │
│ │ • Incorporates image data │ │
│ │ • Sends to LLM for        │ │
│ │   assessment              │ │
│ │                           │ │
│ │ node_generate_report():   │ │
│ │ • Includes image_analysis │ │
│ │   in final report         │ │
│ └───────────────────────────┘ │
│                               │
│ Vision AI Integration:        │
│ ┌───────────────────────────┐ │
│ │ Gemini Vision API         │ │
│ │ (if GEMINI_API_KEY set)   │ │
│ │ Otherwise: Fallback       │ │
│ │ analysis                  │ │
│ └───────────────────────────┘ │
│                               │
│ LLM Integration:              │
│ ┌───────────────────────────┐ │
│ │ Image analysis context    │ │
│ │ is added to triage        │ │
│ │ analysis prompt           │ │
│ └───────────────────────────┘ │
└──────────────────────────────┘
```

## Data Flow Sequence

```
1. USER ACTION SEQUENCE
   ┌─────────────────────────────────────────┐
   │ User enters primary symptom             │
   └─────────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │ Frontend calls POST /generate-questions │
   │ (AI returns 6 follow-up questions)       │
   └─────────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │ [OPTIONAL] User uploads image           │
   │ • Frontend: handleImageSelection()       │
   │ • Shows preview + filename              │
   └─────────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │ User answers 6 follow-up questions      │
   │ • Each answer triggers submitAnswer()    │
   │ • Questions asked one at a time         │
   └─────────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │ [IF IMAGE UPLOADED] analyze it          │
   │ Frontend calls:                          │
   │ POST /analyze-symptom-image-for-triage  │
   │ Returns: imageAnalysis object           │
   └─────────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │ Frontend calls POST /generate-report    │
   │ Includes:                               │
   │ • session_id, symptom, answers          │
   │ • image_analysis (if uploaded)          │
   └─────────────────────────────────────────┘

2. BACKEND PROCESSING
   ┌─────────────────────────────────────────┐
   │ FastAPI receives generate-report        │
   │ Calls: run_report_generation()          │
   └─────────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │ Workflow: node_rag_retrieval()          │
   │ • Retrieves medical knowledge           │
   └─────────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │ Workflow: node_process_answers()        │
   │ • Enriches query with user answers      │
   │ • Re-retrieves relevant documents       │
   └─────────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │ Workflow: node_triage_engine()          │
   │ • Builds assessment prompt              │
   │ • IF image_analysis exists:             │
   │   - Adds image context to prompt        │
   │   - Includes observations, red flags    │
   │ • Calls LLM with combined context       │
   │ • Returns: triage_result                │
   └─────────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │ Workflow: node_generate_explanation()   │
   │ • Creates patient-friendly text         │
   └─────────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │ Workflow: node_generate_report()        │
   │ • Compiles final report                 │
   │ • Includes image_analysis field         │
   │ • Returns complete report               │
   └─────────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │ FastAPI returns report to frontend      │
   └─────────────────────────────────────────┘

3. DATABASE STORAGE
   ┌─────────────────────────────────────────┐
   │ Frontend calls POST /api/reports.php    │
   │ Includes:                               │
   │ • All report fields                     │
   │ • image_analysis as JSON string         │
   └─────────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │ PHP decodes and stores in triage_       │
   │ reports table                           │
   │                                          │
   │ INSERT triage_reports (                 │
   │   user_id, possible_condition,          │
   │   urgency, image_analysis, ...          │
   │ )                                        │
   └─────────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │ Report stored with all data including   │
   │ image analysis results                  │
   └─────────────────────────────────────────┘

4. DISPLAY & RETRIEVAL
   ┌─────────────────────────────────────────┐
   │ Frontend displays report:                │
   │ • Triage assessment                     │
   │ • IF image_analysis:                    │
   │   - Image Analysis Results section      │
   │   - Visible observations                │
   │   - Red flags                           │
   │   - Confidence level                    │
   │   - Disclaimer                          │
   │ • Doctor recommendations                │
   └─────────────────────────────────────────┘
                    ↓
   ┌─────────────────────────────────────────┐
   │ On report retrieval (GET):              │
   │ PHP decodeReportData() parses JSON      │
   │ image_analysis is included in response  │
   └─────────────────────────────────────────┘
```

## Component Interaction Diagram

```
┌──────────────────────────────────────────────────────────────┐
│                                                               │
│  FRONTEND                                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ symptom-chat.html                                      │ │
│  │ • Image upload input                                   │ │
│  │ • Chat messages                                        │ │
│  │ • Report display                                       │ │
│  │                                                         │ │
│  │ symptom-chat.js                                        │ │
│  │ • handleImageSelection()  ──┐                          │ │
│  │ • analyzeSymptomImage()   ──┤──→ AI_BASE/analyze...   │ │
│  │ • generateReportWithImage()─┤──→ AI_BASE/generate...  │ │
│  │ • renderReportPanel()     ──┴──→ Display results      │ │
│  │                                                         │ │
│  │ State:                                                  │ │
│  │ • selectedImageFile                                    │ │
│  │ • imageAnalysis {                                      │ │
│  │    image_type, observations,                           │ │
│  │    red_flags, confidence                               │ │
│  │  }                                                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                       │                                       │
└───────────────────────┼───────────────────────────────────────┘
                        │
                        │ HTTP API Calls
                        │
    ┌───────────────────┴───────────────────┐
    │                                         │
    ▼                                         ▼
┌──────────────────────────────┐   ┌──────────────────────────────┐
│  FastAPI Backend (Python)     │   │  PHP Backend (MySQL)         │
│                               │   │                              │
│  routes/triage.py            │   │  api/reports.php             │
│  ├─ POST /generate-report    │   │  ├─ GET: retrieve reports    │
│  │  • Receives session_id,   │   │  ├─ POST: store reports      │
│  │    symptom, answers,      │   │  └─ PUT: update with image   │
│  │    image_analysis         │   │                              │
│  │                           │   │  Functions:                  │
│  └─ Calls workflow...        │   │  ├─ decodeReportData()       │
│                              │   │  │  (JSON → array)           │
│  workflow.py                 │   │  └─ Store image_analysis     │
│  ├─ TriageState              │   │                              │
│  │  + image_analysis: dict   │   │  Database:                   │
│  │                           │   │  triage_reports             │
│  ├─ node_triage_engine()     │   │  ├─ id                       │
│  │  (new logic):             │   │  ├─ user_id                  │
│  │  • If image_analysis:     │   │  ├─ possible_condition       │
│  │    - Add to prompt        │   │  ├─ image_analysis (NEW)     │
│  │    - Include findings     │   │  ├─ created_at              │
│  │                           │   │  └─ ...other fields          │
│  ├─ node_generate_report()   │   │                              │
│  │  • Include image_analysis │   │  Indexes:                    │
│  │    in report dict         │   │  ├─ id (PK)                  │
│  │                           │   │  ├─ user_id (FK)             │
│  └─ LLM integration          │   │  └─ idx_image_analysis       │
│                              │   │                              │
│  routes/symptom_images.py    │   │                              │
│  ├─ POST /analyze-symptom-   │   │                              │
│  │  image-for-triage (NEW)   │   │                              │
│  │  • Accepts: image file    │   │                              │
│  │  • Analyzes with Gemini   │   │                              │
│  │  • Returns structured     │   │                              │
│  │    analysis               │   │                              │
│  │                           │   │                              │
│  └─ Integration:             │   │                              │
│     • Gemini Vision API      │   │                              │
│     • Fallback if no API     │   │                              │
│                              │   │                              │
│  schemas.py                  │   │                              │
│  • ReportRequest             │   │                              │
│    + image_analysis: dict    │   │                              │
│                              │   │                              │
└──────────────────────────────┘   └──────────────────────────────┘
```

## Database Schema Evolution

```
BEFORE (Original)
┌─────────────────────────────────┐
│     triage_reports              │
├─────────────────────────────────┤
│ id                 INT (PK)      │
│ user_id            INT (FK)      │
│ possible_condition VARCHAR(255)  │
│ urgency            VARCHAR(50)   │
│ reasoning          TEXT          │
│ guidance           TEXT          │
│ explanation        TEXT          │
│ symptoms_listed    JSON          │
│ created_at         TIMESTAMP     │
└─────────────────────────────────┘

AFTER (Enhanced)
┌─────────────────────────────────┐
│     triage_reports              │
├─────────────────────────────────┤
│ id                 INT (PK)      │
│ user_id            INT (FK)      │
│ possible_condition VARCHAR(255)  │
│ urgency            VARCHAR(50)   │
│ reasoning          TEXT          │
│ guidance           TEXT          │
│ explanation        TEXT          │
│ image_analysis     LONGTEXT ◄────┼── NEW COLUMN
│ symptoms_listed    JSON          │
│ created_at         TIMESTAMP     │
└─────────────────────────────────┘

image_analysis JSON Structure:
{
  "image_type": "rash|cut|burn|swelling|unclear",
  "visible_observations": ["obs1", "obs2"],
  "possible_relevance": "text",
  "red_flags": ["flag1"],
  "image_quality": "clear|unclear",
  "confidence": "high|medium|low",
  "needs_clinician_review": true|false,
  "model": "gemini|local_fallback",
  "disclaimer": "..."
}
```

## Request/Response Examples

### 1. Image Analysis Request

```http
POST /analyze-symptom-image-for-triage
Content-Type: multipart/form-data

[binary image data]
```

### 2. Image Analysis Response

```json
{
  "image_type": "rash",
  "visible_observations": [
    "erythema",
    "vesicles present",
    "scattered distribution"
  ],
  "possible_relevance": "Could indicate contact dermatitis or viral exanthem",
  "red_flags": ["widespread vesicles", "high fever"],
  "image_quality": "clear",
  "confidence": "high",
  "needs_clinician_review": true,
  "model": "gemini-2.5-flash-lite",
  "disclaimer": "Image review is supportive only...",
  "analysis_context": "triage",
  "assessment_flag": "yellow"
}
```

### 3. Report Generation Request (with image)

```json
{
  "session_id": "sess_123",
  "symptom": "Red rash on my arm",
  "answers": ["Started 3 days ago", "Moderate severity", "No fever"],
  "user_id": 1,
  "image_analysis": {
    "image_type": "rash",
    "visible_observations": ["erythema", "vesicles"],
    "red_flags": ["widespread"],
    "confidence": "high",
    "assessment_flag": "yellow"
  }
}
```

### 4. Report Generation Response

```json
{
  "report": {
    "session_id": "sess_123",
    "user_id": 1,
    "possible_condition": "Contact Dermatitis",
    "urgency": "medium",
    "recommended_specialist": "Dermatologist",
    "reasoning": "Visual presentation shows erythema consistent with contact dermatitis...",
    "guidance": "Avoid irritants, use moisturizer...",
    "symptoms_listed": ["Red rash on arm"],
    "image_analysis": {
      "image_type": "rash",
      "visible_observations": ["erythema", "vesicles"],
      "red_flags": ["widespread"],
      "confidence": "high"
    },
    "generated_at": "2026-05-07T14:30:00Z"
  }
}
```

---

This architecture ensures:
✅ Clean separation of concerns
✅ Scalable design
✅ Optional image processing
✅ Backward compatibility
✅ Professional-grade assessment
