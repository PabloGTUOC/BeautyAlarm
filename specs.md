# Project Specification: Beauty Routine Tracker

## 1. Overview
A cross-platform tracking application designed to manage daily beauty and skincare routines. The system allows users to schedule treatments, configure product usage based on specific days and times (morning/night), receive mobile notifications when treatments are due, and log daily completions.

## 2. Technology Stack
*   **Frontend:** Flutter (Mobile application for iOS/Android)
*   **Backend:** FastAPI (Python)
*   **Database:** MySQL
*   **Deployment:** Docker & Docker Compose

## 3. Core Features
*   **Routine Configuration:**
    *   Add and manage products and treatments.
    *   Assign routines to specific days of the week.
    *   Categorize by time of day (Morning / Night).
*   **Notification System:**
    *   Mobile push notifications triggered when a treatment is due based on user-defined times.
*   **Progress & Tracking:**
    *   Daily checklist interface to mark routines as 'Completed' for the day.
    *   Visual calendar or streak view to review consistency.

## 4. Infrastructure & Deployment Strategy
The application is architected for self-hosted execution.
*   **Target Environment:** AMD Ryzen host, 16GB RAM (NAS/Home Server).
*   **Containerization:** A single `docker-compose.yml` orchestrating:
    *   `api`: FastAPI application serving REST endpoints.
    *   `db`: MySQL database with persistent volume mapping to local NAS storage.
*   **Networking:** Secure external routing via Cloudflare Tunnels to allow the Flutter mobile app to communicate securely with the backend APIs without exposing local ports or requiring a VPN.

## 5. High-Level Data Model (MySQL)
*   **`User`**: (Optional, if multi-user support is needed) `id`, `username`, `timezone`
*   **`Product`**: `id`, `name`, `brand`, `notes`
*   **`Routine`**: `id`, `product_id`, `days_of_week` (JSON/Bitmask), `time_period` (Morning/Night), `notification_time`
*   **`DailyLog`**: `id`, `routine_id`, `timestamp`, `status` (Completed/Skipped)

## 6. Antigravity Kickoff / Next Steps
1.  **Backend:** Initialize FastAPI scaffolding with SQLAlchemy as the ORM to interact with MySQL. Set up Alembic for migrations.
2.  **Infrastructure:** Draft the Dockerfile for FastAPI and the `docker-compose.yml` to spin up both the API and Database securely.
3.  **Frontend:** Initialize the Flutter project. Configure state management and integrate a local notification package (e.g., `flutter_local_notifications`) or FCM for remote push triggers.
4.  **API Integration:** Build out the CRUD endpoints and integrate them into the Flutter UI.
