# KrishiSaathi - Design Document

## AI-Powered Multi-Agent Agricultural Intelligence System

---

### Document Information

| Field | Details |
|-------|---------|
| **Project Name** | KrishiSaathi |
| **Version** | 1.0 |
| **Date** | February 4, 2026 |
| **Hackathon** | AWS AI for Bharat Hackathon 2026 |
| **Track** | AI for Rural Innovation & Sustainable Systems |

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Component Design](#2-component-design)
3. [Data Flow Design](#3-data-flow-design)
4. [API Design](#4-api-design)
5. [Database Schema](#5-database-schema)
6. [External Integrations](#6-external-integrations)
7. [Security Design](#7-security-design)
8. [Deployment Architecture](#8-deployment-architecture)

---

## 1. System Architecture

### 1.1 High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│  📱 PWA Client     │  💬 WhatsApp Bot  │  📞 IVR System  │  📱 SMS Gateway  │
│  (React.js)        │  (Twilio API)     │  (Amazon Connect)│  (AWS SNS)       │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │ HTTPS/WSS
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY LAYER                                   │
├──────────────────────────────────────────────────────────────────────────────┤
│  🌐 Amazon API Gateway                                                        │
│  ├── REST API Endpoints (/api/v1/*)                                          │
│  ├── WebSocket API (real-time updates)                                       │
│  ├── Request Validation & Throttling                                         │
│  └── CORS Configuration                                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│  🔐 Amazon Cognito                                                           │
│  ├── User Authentication (Phone/Email)                                       │
│  ├── JWT Token Management                                                    │
│  └── User Profile Storage                                                    │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         PROCESSING LAYER                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│  ⚡ AWS Lambda Functions                                                      │
│  ├── Input Processor        - Language detection, media processing           │
│  ├── Agent Router           - Route to appropriate Bedrock agent             │
│  ├── Response Formatter     - Format responses for each channel              │
│  ├── Notification Service   - Send alerts and reminders                      │
│  └── Analytics Processor    - Log events and metrics                         │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                     AMAZON BEDROCK MULTI-AGENT LAYER                          │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                      SUPERVISOR AGENT                                    │ │
│  │                 (Amazon Bedrock Agent - Claude 3.5 Sonnet)              │ │
│  │  ┌───────────────────────────────────────────────────────────────────┐  │ │
│  │  │ • Intent Classification    • Agent Routing    • Context Injection │  │ │
│  │  │ • Response Synthesis       • Memory Management • Guardrails       │  │ │
│  │  └───────────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────┬───────────────────────────────────────┘ │
│                                    │                                          │
│    ┌──────────┬──────────┬─────────┴─────────┬──────────┬──────────┐        │
│    ▼          ▼          ▼                   ▼          ▼          │        │
│ ┌────────┐┌────────┐┌──────────┐      ┌──────────┐┌──────────┐     │        │
│ │  CROP  ││ MARKET ││  SCHEME  │      │ WEATHER  ││   SOIL   │     │        │
│ │ DOCTOR ││ANALYST ││ ADVISOR  │      │ PROPHET  ││  EXPERT  │     │        │
│ │        ││        ││          │      │          ││          │     │        │
│ │Bedrock ││Bedrock ││ Bedrock  │      │ Bedrock  ││ Bedrock  │     │        │
│ │ Agent  ││ Agent  ││  Agent   │      │  Agent   ││  Agent   │     │        │
│ └────┬───┘└────┬───┘└────┬─────┘      └────┬─────┘└────┬─────┘     │        │
│      │         │         │                 │           │           │        │
└──────┼─────────┼─────────┼─────────────────┼───────────┼───────────┼────────┘
       │         │         │                 │           │           │
       ▼         ▼         ▼                 ▼           ▼           ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    RAG KNOWLEDGE LAYER                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│  📚 Amazon Bedrock Knowledge Bases                                            │
│  ├── ICAR Research Papers (10,000+ documents)                                │
│  ├── Crop Disease Database (5,000+ entries)                                  │
│  ├── Government Scheme Repository (500+ schemes)                             │
│  ├── Regional Best Practices (15,000+ documents)                             │
│  └── Pest & Fertilizer Guides (20,000+ documents)                            │
├──────────────────────────────────────────────────────────────────────────────┤
│  🔍 Amazon OpenSearch Serverless                                              │
│  ├── Vector Store (Amazon Titan Embeddings V2)                               │
│  ├── Semantic Search Index                                                   │
│  └── Hybrid Search (Vector + Keyword)                                        │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                     EXTERNAL INTEGRATIONS LAYER                               │
├──────────────────────────────────────────────────────────────────────────────┤
│  🌤️ IMD Weather API    │  💰 eNAM Mandi API   │  🏛️ PM-KISAN API            │
│  🛰️ Satellite Imagery   │  🔬 Soil Health Card  │  📊 Agmarknet               │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                            │
├──────────────────────────────────────────────────────────────────────────────┤
│  📊 Amazon DynamoDB     │  🪣 Amazon S3         │  📈 Amazon CloudWatch       │
│  ├── User Profiles      │  ├── Document Storage │  ├── Logs & Metrics         │
│  ├── Conversation History│ ├── Image Storage    │  ├── Dashboards             │
│  ├── Farm Data          │  └── Model Artifacts  │  └── Alerts                 │
│  └── Price Cache        │                       │                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 1.2 Technology Stack Summary

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React.js, Tailwind CSS, PWA | Mobile-first web application |
| **API Gateway** | Amazon API Gateway | REST & WebSocket endpoints |
| **Authentication** | Amazon Cognito | User auth & profile management |
| **Compute** | AWS Lambda | Serverless processing |
| **AI/ML Core** | Amazon Bedrock (Claude 3.5 Sonnet) | Multi-agent orchestration |
| **Knowledge Base** | Amazon Bedrock Knowledge Bases | RAG implementation |
| **Vector Database** | Amazon OpenSearch Serverless | Embedding storage & search |
| **Speech** | Amazon Transcribe, Amazon Polly | Voice I/O |
| **Translation** | Amazon Translate | Multi-language support |
| **Computer Vision** | Amazon Rekognition | Disease detection |
| **Database** | Amazon DynamoDB | NoSQL data storage |
| **Storage** | Amazon S3 | File & document storage |
| **Messaging** | AWS SNS, Twilio | SMS & WhatsApp |
| **Monitoring** | Amazon CloudWatch | Logs, metrics, alerts |

---

## 2. Component Design

### 2.1 Supervisor Agent Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUPERVISOR AGENT                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │ INTENT          │    │ CONTEXT         │    │ AGENT           │         │
│  │ CLASSIFIER      │───▶│ ENRICHER        │───▶│ ROUTER          │         │
│  │                 │    │                 │    │                 │         │
│  │ • Crop Disease  │    │ • User Profile  │    │ • Single Agent  │         │
│  │ • Market Query  │    │ • Farm Data     │    │ • Multi-Agent   │         │
│  │ • Scheme Query  │    │ • Season        │    │ • Parallel Call │         │
│  │ • Weather Query │    │ • Location      │    │                 │         │
│  │ • Soil Query    │    │ • History       │    │                 │         │
│  └─────────────────┘    └─────────────────┘    └────────┬────────┘         │
│                                                          │                  │
│                                                          ▼                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐         │
│  │ RESPONSE        │◀───│ GUARDRAILS      │◀───│ RESPONSE        │         │
│  │ FORMATTER       │    │ VALIDATOR       │    │ SYNTHESIZER     │         │
│  │                 │    │                 │    │                 │         │
│  │ • Language      │    │ • Safety Check  │    │ • Combine       │         │
│  │ • Channel       │    │ • Accuracy      │    │ • Prioritize    │         │
│  │ • Format        │    │ • Relevance     │    │ • Summarize     │         │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Supervisor Agent Configuration

```yaml
SupervisorAgent:
  name: "KrishiSaathi-Supervisor"
  model: "anthropic.claude-3-5-sonnet-20241022-v2:0"
  instructions: |
    You are KrishiSaathi, an AI farming assistant for Indian farmers.
    Your role is to understand farmer queries and route them to specialist agents.
    
    Routing Rules:
    - Disease/pest/crop health → Crop Doctor Agent
    - Prices/market/selling → Market Intelligence Agent  
    - Schemes/subsidies/government → Scheme Advisor Agent
    - Weather/rain/temperature → Weather Prophet Agent
    - Soil/fertilizer/nutrients → Soil Expert Agent
    - Complex queries → Invoke multiple agents in parallel
    
    Context Injection:
    - Always include user's location, crops, and farm size
    - Consider current season and recent weather
    - Reference previous conversation context
    
    Response Guidelines:
    - Be concise and actionable
    - Use simple language
    - Provide specific recommendations
    - Include next steps when relevant
  
  memory:
    enabled: true
    retention_days: 30
  
  guardrails:
    content_filter: true
    accuracy_check: true
    bias_detection: true
```

---

### 2.2 Specialist Agent Designs

#### 2.2.1 Crop Doctor Agent

```yaml
CropDoctorAgent:
  name: "KrishiSaathi-CropDoctor"
  model: "anthropic.claude-3-5-sonnet-20241022-v2:0"
  knowledge_base: "kb-crop-diseases"
  
  tools:
    - name: "analyze_crop_image"
      description: "Analyze uploaded crop image for disease detection"
      api: "Amazon Rekognition Custom Labels"
      
    - name: "get_treatment_recommendation"
      description: "Get treatment recommendations from knowledge base"
      api: "Bedrock Knowledge Base Query"
      
    - name: "find_nearby_stores"
      description: "Find agricultural stores near user location"
      api: "Google Places API"
      
    - name: "set_reminder"
      description: "Set treatment reminder for farmer"
      api: "AWS EventBridge"
  
  instructions: |
    You are a crop disease expert. Analyze crop images and symptoms to:
    1. Identify the disease/pest with confidence score
    2. Explain the cause and severity
    3. Provide specific treatment with dosage
    4. Suggest preventive measures
    5. Recommend when to reapply treatment
    
    Always provide organic alternatives when available.
    Warn about safety precautions for chemical treatments.
```

#### 2.2.2 Market Intelligence Agent

```yaml
MarketIntelligenceAgent:
  name: "KrishiSaathi-MarketAnalyst"
  model: "anthropic.claude-3-5-sonnet-20241022-v2:0"
  knowledge_base: "kb-market-data"
  
  tools:
    - name: "get_mandi_prices"
      description: "Fetch real-time prices from eNAM and Agmarknet"
      api: "eNAM API + Agmarknet API"
      
    - name: "predict_prices"
      description: "7-day price prediction using ML model"
      api: "SageMaker Endpoint"
      
    - name: "calculate_transport_cost"
      description: "Calculate transport cost to different mandis"
      api: "Distance Matrix API"
      
    - name: "find_buyers"
      description: "Find verified bulk buyers in the region"
      api: "Buyer Database Query"
  
  instructions: |
    You are a market intelligence expert. Help farmers:
    1. Find current prices at nearby mandis
    2. Predict price trends for next 7 days
    3. Recommend best mandi considering price + transport cost
    4. Suggest optimal timing for selling
    5. Connect with bulk buyers when relevant
    
    Always show confidence levels for predictions.
    Consider transport costs in recommendations.
```

#### 2.2.3 Government Scheme Advisor Agent

```yaml
SchemeAdvisorAgent:
  name: "KrishiSaathi-SchemeAdvisor"
  model: "anthropic.claude-3-5-sonnet-20241022-v2:0"
  knowledge_base: "kb-government-schemes"
  
  tools:
    - name: "check_eligibility"
      description: "Check farmer eligibility for schemes"
      api: "Scheme Rules Engine"
      
    - name: "get_scheme_details"
      description: "Fetch scheme details from knowledge base"
      api: "Bedrock Knowledge Base Query"
      
    - name: "generate_document_checklist"
      description: "Generate required documents list"
      api: "Document Template Engine"
      
    - name: "track_application"
      description: "Track application status"
      api: "Government Portal APIs"
  
  instructions: |
    You are a government scheme expert. Help farmers:
    1. Identify all eligible schemes based on profile
    2. Explain benefits and eligibility criteria
    3. Provide step-by-step application guidance
    4. Generate document checklists
    5. Track existing applications
    
    Prioritize schemes by benefit amount.
    Explain complex terms in simple language.
```

#### 2.2.4 Weather Prophet Agent

```yaml
WeatherProphetAgent:
  name: "KrishiSaathi-WeatherProphet"
  model: "anthropic.claude-3-5-sonnet-20241022-v2:0"
  knowledge_base: "kb-weather-agriculture"
  
  tools:
    - name: "get_weather_forecast"
      description: "Get 7-day weather forecast for location"
      api: "IMD Weather API"
      
    - name: "get_historical_weather"
      description: "Fetch historical weather patterns"
      api: "Weather Database Query"
      
    - name: "generate_crop_alert"
      description: "Generate crop-specific weather alerts"
      api: "Alert Rules Engine"
      
    - name: "predict_sowing_window"
      description: "Predict optimal sowing dates"
      api: "ML Prediction Model"
  
  instructions: |
    You are a weather and agricultural timing expert. Help farmers:
    1. Provide accurate village-level weather forecasts
    2. Generate crop-specific alerts (spray timing, irrigation, harvest)
    3. Warn about upcoming disasters
    4. Recommend optimal dates for farming activities
    5. Explain weather impact on crops
    
    Always provide actionable recommendations.
    Include confidence levels for predictions.
```

#### 2.2.5 Soil Expert Agent

```yaml
SoilExpertAgent:
  name: "KrishiSaathi-SoilExpert"
  model: "anthropic.claude-3-5-sonnet-20241022-v2:0"
  knowledge_base: "kb-soil-management"
  
  tools:
    - name: "get_soil_health_data"
      description: "Fetch data from Soil Health Card portal"
      api: "Soil Health Card API"
      
    - name: "calculate_fertilizer"
      description: "Calculate NPK requirements"
      api: "Fertilizer Calculator Engine"
      
    - name: "suggest_organic_alternatives"
      description: "Find organic fertilizer options"
      api: "Organic Database Query"
      
    - name: "plan_crop_rotation"
      description: "Generate crop rotation plan"
      api: "Rotation Planner Engine"
  
  instructions: |
    You are a soil health expert. Help farmers:
    1. Interpret soil health card results
    2. Calculate precise fertilizer requirements
    3. Suggest organic alternatives
    4. Recommend crop rotation for soil improvement
    5. Guide on soil testing procedures
    
    Consider crop growth stage in recommendations.
    Prioritize soil health over short-term yields.
```

---

## 3. Data Flow Design

### 3.1 User Query Processing Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INPUT                                      │
│   Voice 🎤  /  Text 💬  /  Image 📷  /  WhatsApp 💬  /  SMS 📱              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 1: INPUT PROCESSING                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐     │
│  │  Language   │   │  Speech to  │   │   Image     │   │ Translation │     │
│  │  Detection  │──▶│    Text     │──▶│ Processing  │──▶│ to English  │     │
│  │ (Comprehend)│   │(Transcribe) │   │(Rekognition)│   │ (Translate) │     │
│  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘     │
│                                                                              │
│  Output: Normalized text query + detected language + processed images       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 2: CONTEXT ENRICHMENT                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐     │
│  │    User     │   │    Farm     │   │  Seasonal   │   │ Conversation│     │
│  │   Profile   │ + │    Data     │ + │   Context   │ + │   History   │     │
│  │ (DynamoDB)  │   │ (DynamoDB)  │   │  (Current)  │   │  (Memory)   │     │
│  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘     │
│                                                                              │
│  Output: Enriched query with full context                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 3: SUPERVISOR AGENT PROCESSING                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    INTENT CLASSIFICATION                             │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │   │
│  │  │  Crop    │ │  Market  │ │  Scheme  │ │  Weather │ │   Soil   │  │   │
│  │  │  Health  │ │   Price  │ │  Query   │ │   Query  │ │   Query  │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                    ┌───────────────┴───────────────┐                       │
│                    ▼                               ▼                        │
│           Single Agent Route              Multi-Agent Route                 │
│           (One specialist)                (Parallel invocation)             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 4: SPECIALIST AGENT EXECUTION                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Each agent performs:                                                        │
│  1. Query relevant knowledge base (RAG)                                     │
│  2. Call external APIs if needed                                            │
│  3. Apply domain-specific reasoning                                         │
│  4. Generate structured response                                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 5: RESPONSE SYNTHESIS                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐     │
│  │   Combine   │   │  Guardrails │   │  Translate  │   │   Format    │     │
│  │  Responses  │──▶│   Check     │──▶│ to User     │──▶│ for Channel │     │
│  │             │   │  (Bedrock)  │   │  Language   │   │             │     │
│  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STEP 6: RESPONSE DELIVERY                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐     │
│  │    Text     │   │   Voice     │   │    Rich     │   │   Action    │     │
│  │  Response   │ + │  Response   │ + │   Cards     │ + │   Buttons   │     │
│  │             │   │   (Polly)   │   │             │   │             │     │
│  └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 3.2 Multi-Agent Collaboration Flow

```
Query: "My tomato has pests. Should I spray today?"

┌─────────────────────────────────────────────────────────────────────────────┐
│                         SUPERVISOR AGENT                                     │
│   Analysis: Multi-domain query requiring Crop Doctor + Weather Prophet      │
│   Action: Invoke both agents in PARALLEL                                    │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                ┌───────────────┴───────────────┐
                │                               │
                ▼                               ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│      CROP DOCTOR          │   │     WEATHER PROPHET       │
│                           │   │                           │
│  Step 1: Identify pest    │   │  Step 1: Get location     │
│  Step 2: Query KB for     │   │  Step 2: Fetch 24hr       │
│          treatment        │   │          forecast         │
│  Step 3: Get dosage       │   │  Step 3: Check humidity   │
│          details          │   │          and rain prob    │
│                           │   │                           │
│  Response:                │   │  Response:                │
│  "White fly infestation   │   │  "Rain expected in 6hrs   │
│   detected. Recommend     │   │   Humidity: 78%           │
│   Imidacloprid 17.8 SL    │   │   Not suitable for        │
│   @ 0.5ml/liter"          │   │   spraying today"         │
└─────────────┬─────────────┘   └─────────────┬─────────────┘
              │                               │
              └───────────────┬───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SUPERVISOR AGENT (Synthesis)                              │
│                                                                              │
│  Combines both responses into coherent actionable advice:                   │
│                                                                              │
│  "Your tomato crop has White Fly infestation.                               │
│                                                                              │
│   Treatment: Imidacloprid 17.8 SL @ 0.5ml/liter water                       │
│                                                                              │
│   ⚠️ BUT DON'T SPRAY TODAY!                                                 │
│   Rain is expected in 6 hours. Spraying now will wash away the pesticide.  │
│                                                                              │
│   📅 Best time to spray: Tomorrow morning 6-9 AM                            │
│   🔔 I'll send you a reminder tomorrow at 6 AM"                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. API Design

### 4.1 REST API Endpoints

#### Authentication APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | User login |
| POST | `/api/v1/auth/verify-otp` | Verify OTP |
| POST | `/api/v1/auth/refresh` | Refresh JWT token |
| POST | `/api/v1/auth/logout` | User logout |

#### Chat APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat/message` | Send message to AI |
| POST | `/api/v1/chat/voice` | Send voice message |
| POST | `/api/v1/chat/image` | Send image for analysis |
| GET | `/api/v1/chat/history` | Get conversation history |
| DELETE | `/api/v1/chat/history` | Clear conversation history |

#### User Profile APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/user/profile` | Get user profile |
| PUT | `/api/v1/user/profile` | Update user profile |
| POST | `/api/v1/user/farm` | Add farm details |
| PUT | `/api/v1/user/farm/{farmId}` | Update farm details |
| GET | `/api/v1/user/preferences` | Get user preferences |
| PUT | `/api/v1/user/preferences` | Update preferences |

#### Market APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/market/prices/{crop}` | Get crop prices |
| GET | `/api/v1/market/nearby` | Get nearby mandis |
| GET | `/api/v1/market/prediction/{crop}` | Get price prediction |
| POST | `/api/v1/market/alerts` | Set price alert |

#### Weather APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/weather/forecast` | Get weather forecast |
| GET | `/api/v1/weather/alerts` | Get weather alerts |
| POST | `/api/v1/weather/subscribe` | Subscribe to alerts |

#### Scheme APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/schemes/eligible` | Get eligible schemes |
| GET | `/api/v1/schemes/{schemeId}` | Get scheme details |
| GET | `/api/v1/schemes/{schemeId}/documents` | Get required documents |
| POST | `/api/v1/schemes/{schemeId}/apply` | Start application |

---

### 4.2 Request/Response Examples

#### Chat Message Request

```json
{
  "message": "My wheat leaves are turning yellow",
  "type": "text",
  "language": "en",
  "location": {
    "latitude": 28.6139,
    "longitude": 77.2090
  },
  "attachments": []
}
```

#### Chat Message Response

```json
{
  "response_id": "resp_abc123",
  "message": "I can see your wheat leaves are yellowing. This could be due to several reasons...",
  "agent": "crop_doctor",
  "confidence": 0.92,
  "actions": [
    {
      "type": "image_request",
      "message": "Can you please upload a photo of the affected leaves?"
    }
  ],
  "suggestions": [
    "Show me treatment options",
    "Find nearby agri store",
    "Set a reminder"
  ],
  "audio_url": "https://s3.../response_audio.mp3",
  "timestamp": "2026-02-04T10:30:00Z"
}
```

---

## 5. Database Schema

### 5.1 DynamoDB Tables

#### Users Table

```
Table: krishisaathi-users
Partition Key: user_id (String)

Attributes:
├── user_id          (String)    - Unique user identifier
├── phone_number     (String)    - Phone number (verified)
├── name             (String)    - User's name
├── preferred_language (String)  - hi, ta, te, en, etc.
├── location         (Map)       - {lat, lng, district, state}
├── created_at       (String)    - ISO timestamp
├── updated_at       (String)    - ISO timestamp
└── settings         (Map)       - User preferences

GSI: phone-index (phone_number)
```

#### Farms Table

```
Table: krishisaathi-farms
Partition Key: user_id (String)
Sort Key: farm_id (String)

Attributes:
├── user_id          (String)    - Owner user ID
├── farm_id          (String)    - Unique farm identifier
├── name             (String)    - Farm name
├── location         (Map)       - {lat, lng, village, district}
├── area_acres       (Number)    - Farm area
├── soil_type        (String)    - Soil classification
├── irrigation_type  (String)    - Irrigation method
├── crops            (List)      - Current crops [{name, variety, sowing_date}]
├── soil_health_card (Map)       - Soil test results
└── created_at       (String)    - ISO timestamp
```

#### Conversations Table

```
Table: krishisaathi-conversations
Partition Key: user_id (String)
Sort Key: timestamp (String)

Attributes:
├── user_id          (String)    - User identifier
├── timestamp        (String)    - ISO timestamp
├── session_id       (String)    - Conversation session
├── message          (String)    - User message
├── response         (String)    - AI response
├── agent            (String)    - Agent that handled query
├── intent           (String)    - Detected intent
├── language         (String)    - Conversation language
├── channel          (String)    - pwa, whatsapp, sms
└── attachments      (List)      - Media attachments

GSI: session-index (session_id, timestamp)
TTL: 90 days
```

#### Price Cache Table

```
Table: krishisaathi-price-cache
Partition Key: crop_code (String)
Sort Key: mandi_code (String)

Attributes:
├── crop_code        (String)    - Crop identifier
├── mandi_code       (String)    - Mandi identifier
├── crop_name        (String)    - Crop name
├── mandi_name       (String)    - Mandi name
├── state            (String)    - State name
├── min_price        (Number)    - Minimum price
├── max_price        (Number)    - Maximum price
├── modal_price      (Number)    - Modal price
├── arrival_qty      (Number)    - Arrival quantity
├── price_date       (String)    - Price date
└── updated_at       (String)    - Last update time

TTL: 24 hours
```

---

## 6. External Integrations

### 6.1 Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INTEGRATION LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    API GATEWAY (AWS Lambda)                          │   │
│  │  • Rate Limiting    • Retry Logic    • Error Handling    • Caching  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│    ┌───────────┬───────────┬───────┴───────┬───────────┬───────────┐       │
│    ▼           ▼           ▼               ▼           ▼           │       │
│ ┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │       │
│ │  eNAM  │ │  IMD   │ │ PM-KISAN │ │   Soil   │ │  Twilio  │       │       │
│ │  API   │ │Weather │ │  Portal  │ │  Health  │ │WhatsApp  │       │       │
│ │        │ │  API   │ │   API    │ │ Card API │ │   API    │       │       │
│ └────────┘ └────────┘ └──────────┘ └──────────┘ └──────────┘       │       │
│                                                                      │       │
└──────────────────────────────────────────────────────────────────────┘       │
```

### 6.2 Integration Details

| Integration | Type | Refresh Rate | Fallback |
|-------------|------|--------------|----------|
| eNAM Mandi Prices | REST API | Every 30 min | Cached data |
| Agmarknet Prices | REST API | Every 1 hour | eNAM data |
| IMD Weather | REST API | Every 3 hours | OpenWeather API |
| Soil Health Card | REST API | On demand | Cached profile |
| PM-KISAN Status | REST API | On demand | Last known status |
| Twilio WhatsApp | Webhook | Real-time | SMS fallback |

---

## 7. Security Design

### 7.1 Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SECURITY LAYERS                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Layer 1: Network Security                                                   │
│  ├── AWS WAF (Web Application Firewall)                                     │
│  ├── DDoS Protection (AWS Shield)                                           │
│  └── VPC with Private Subnets                                               │
│                                                                              │
│  Layer 2: API Security                                                       │
│  ├── TLS 1.3 Encryption (in transit)                                        │
│  ├── API Gateway Throttling                                                 │
│  ├── Request Validation                                                     │
│  └── CORS Configuration                                                     │
│                                                                              │
│  Layer 3: Authentication & Authorization                                     │
│  ├── Amazon Cognito (User Pools)                                            │
│  ├── JWT Token Validation                                                   │
│  ├── OAuth 2.0 Flows                                                        │
│  └── Role-Based Access Control                                              │
│                                                                              │
│  Layer 4: Data Security                                                      │
│  ├── AES-256 Encryption (at rest)                                           │
│  ├── KMS Key Management                                                     │
│  ├── Data Masking for PII                                                   │
│  └── Secure S3 Bucket Policies                                              │
│                                                                              │
│  Layer 5: AI Safety                                                          │
│  ├── Amazon Bedrock Guardrails                                              │
│  ├── Content Filtering                                                      │
│  ├── Prompt Injection Protection                                            │
│  └── Response Validation                                                    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Data Privacy Measures

| Measure | Implementation |
|---------|----------------|
| Consent Management | Explicit opt-in during registration |
| Data Minimization | Collect only necessary information |
| Anonymization | Remove PII from analytics data |
| Right to Deletion | Self-service account deletion |
| Data Portability | Export user data on request |
| Audit Logging | All data access logged in CloudWatch |

---

## 8. Deployment Architecture

### 8.1 Multi-Region Deployment

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GLOBAL INFRASTRUCTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                    ┌─────────────────────────┐                              │
│                    │    Amazon CloudFront    │                              │
│                    │    (Global CDN)         │                              │
│                    └───────────┬─────────────┘                              │
│                                │                                             │
│                    ┌───────────┴─────────────┐                              │
│                    │    Amazon Route 53      │                              │
│                    │    (DNS + Health Check) │                              │
│                    └───────────┬─────────────┘                              │
│                                │                                             │
│        ┌───────────────────────┼───────────────────────┐                    │
│        │                       │                       │                    │
│        ▼                       ▼                       ▼                    │
│  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐            │
│  │   REGION:    │       │   REGION:    │       │   REGION:    │            │
│  │   ap-south-1 │       │  ap-south-2  │       │   Future     │            │
│  │   (Mumbai)   │       │  (Hyderabad) │       │   Expansion  │            │
│  │              │       │              │       │              │            │
│  │  PRIMARY     │       │  SECONDARY   │       │              │            │
│  │  All Services│       │  DR Standby  │       │              │            │
│  └──────────────┘       └──────────────┘       └──────────────┘            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 CI/CD Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CI/CD PIPELINE                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐   │
│  │  Code   │    │  Build  │    │  Test   │    │ Deploy  │    │ Monitor │   │
│  │  Push   │───▶│  & Lint │───▶│  Suite  │───▶│ Staging │───▶│ & Alert │   │
│  │         │    │         │    │         │    │         │    │         │   │
│  │ GitHub  │    │CodeBuild│    │ Unit +  │    │ CDK     │    │CloudWatch│  │
│  │         │    │         │    │ Integ   │    │ Deploy  │    │         │   │
│  └─────────┘    └─────────┘    └─────────┘    └────┬────┘    └─────────┘   │
│                                                     │                       │
│                                              ┌──────▼──────┐                │
│                                              │  Manual     │                │
│                                              │  Approval   │                │
│                                              └──────┬──────┘                │
│                                                     │                       │
│                                              ┌──────▼──────┐                │
│                                              │  Production │                │
│                                              │  Deployment │                │
│                                              └─────────────┘                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Monitoring & Observability

### 9.1 Monitoring Stack

| Component | Tool | Metrics |
|-----------|------|---------|
| Application Logs | CloudWatch Logs | Errors, requests, latency |
| Metrics | CloudWatch Metrics | CPU, memory, API calls |
| Tracing | AWS X-Ray | Request traces, dependencies |
| Dashboards | CloudWatch Dashboards | Real-time visualization |
| Alerts | CloudWatch Alarms | Error rate, latency thresholds |
| Cost | AWS Cost Explorer | Service-wise spending |

### 9.2 Key Metrics to Monitor

| Metric | Threshold | Alert |
|--------|-----------|-------|
| API Response Time | > 3 seconds | Warning |
| Error Rate | > 1% | Critical |
| Disease Detection Accuracy | < 90% | Warning |
| Agent Invocation Failures | > 0.5% | Warning |
| Knowledge Base Query Latency | > 1 second | Warning |
| Concurrent Users | > 80% capacity | Warning |

---

## 10. Conclusion

This design document provides a comprehensive blueprint for implementing KrishiSaathi, an AI-powered multi-agent agricultural intelligence system. The architecture leverages AWS services for scalability, reliability, and cost-effectiveness while delivering a voice-first, multilingual experience tailored for Indian farmers.

Key design principles followed:
- **Serverless-first**: Minimizes operational overhead
- **Multi-agent collaboration**: Specialized agents for accurate domain responses
- **Offline-capable**: Works in low-connectivity rural areas
- **Voice-first**: Accessible to semi-literate users
- **Secure by design**: Protects farmer data and privacy

---

**Document Status**: Final v1.0  
**Prepared for**: AWS AI for Bharat Hackathon 2026  
**Track**: AI for Rural Innovation & Sustainable Systems
