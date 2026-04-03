Product Requirements Document (PRD) - MVP Phase
Project Name: Agentic Vehicle Diagnosis Webapp
Platform: Mobile-first Web Application
Team Structure: Frontend (UI/UX & State), Backend (REST API), AI (LLM & Agents), Hardware (OBD-II integration).

1. Product Overview
An AI-powered automotive assistant that reads read-only OBD-II diagnostic data, translates complex error codes into plain language, estimates repair costs by scraping web data, and tracks routine maintenance. The goal is to empower vehicle owners with transparent, actionable insights without requiring technical automotive knowledge.

2. Target Audience & Market
Everyday car owners who want to avoid being overcharged by mechanics. The interface must support bilingual capabilities (English and Arabic) to accommodate local terms like "الصيانة الدورية" (Routine Maintenance) and display cost estimations in local currency (e.g., SAR ﷼).

3. Core Features & User Flows

Flow 1: Garage Onboarding (Progressive Disclosure)

User lands on "Add Vehicle" screen.

Path A (Auto): User clicks "Auto-Detect via OBD-II" (Simulated loading state for MVP).

Path B (Manual): Step-by-step progressive selection: Make -> Model -> Year -> Current Mileage.

Flow 2: Dashboard (The Hub)

Displays active vehicle details.

High-level health score: Safe to Drive (Green), Drive with Caution (Yellow), Stop Immediately (Red).

Quick alert for the next upcoming routine maintenance milestone.

Flow 3: Diagnostic Report (The Clean UI)

Triggered after a scan. Data is categorized logically (Engine, Electrical, etc.).

"Explain Like I'm 5" translation of AI output.

Cost Estimate Card: Web-scraped estimates split into Parts vs. Labor.

Flow 4: Routine Maintenance (الصيانة الدورية)

Timeline or progress-bar view of required services (e.g., Oil change, brake pads) based on the current mileage and manufacturer manual.

Flow 5: AI Mechanic Chat

Dedicated chat interface.

Pre-loaded context chips (e.g., "Tell me more about code P0171", "Can I fix this myself?").

4. Frontend Engineering Constraints

API Agnostic: Because REST API documentation is pending, the frontend must rely entirely on a robust mockData.js structure.

State Management: Must preserve the selected car data and the generated report across different tabs (Dashboard, Maintenance, Chat).