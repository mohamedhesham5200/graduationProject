# Graduation Project: Learnify (Gamified LMS)

## Project Structure Overview

This project is organized into several main directories, each serving a specific purpose in the development, documentation, and presentation of the Learnify platform.

---

### 1. SourceCode/
- **Purpose:** Contains the main source code for the Learnify platform (Frontend, Backend, and Machine Learning).
- **Frontend:** Built with React "Node.js v20.18.2" (see `package.json` for dependencies and version info). Uses Vite for development and build, and includes modern libraries such as Redux, TailwindCSS, Chart.js, and Stripe integration.
- **Backend:** Built with .NET SDK 6.0+ and SQL Server. Handles business logic, API endpoints, and database interactions.
- **Note:** This folder may include subfolders for `client` (frontend), `server` (backend) and `ML` (Machine Learning).

---

### 2. Database(SQL_Server)/
- **Purpose:** Contains SQL Server database scripts, schema definitions, and possibly backup files.
- **Usage:** Use these scripts to set up the database required for the backend services.

---

### 3. Diagrams/
- **Purpose:** Contains system architecture diagrams, ER diagrams, flowcharts, and other visual documentation.
- **Usage:** Refer to these diagrams for a visual understanding of the system design and data flow.

---

### 4. Presentation/
- **Purpose:** Contains materials for project presentation, Show in PowerPoint slides.
- **Usage:** Use Power Point to present the project to evaluators or stakeholders.

---

### 5. Documentation/
- **Purpose:** Contains detailed documentation, including user manuals, API documentation, and technical reports.
- **Usage:** Refer to this folder for in-depth explanations of system features, setup instructions, and usage guidelines.

---

## Database Configuration

To run the project correctly, you need to update the database connection string in the `appsettings.json` file. Follow these steps:

1. Open the `appsettings.json` file in your backend project.
2. Locate the `ConnectionStrings` section.
3. Replace the existing connection string with your desired database connection string. For example:

   ```json
   "ConnectionStrings": {
     "defaultconnection": "data source=YOUR_SERVER;initial catalog=YOUR_DATABASE;user id=YOUR_USERNAME;password=YOUR_PASSWORD"
   }
   ```

4. Save the file and restart your backend application.

**Note:** Ensure that your database server is accessible and that the credentials provided are correct.

**Limitations:**
- The database connection string must be valid and correctly formatted.
- Ensure that the database server is running and accessible from your application.
- The user credentials must have the necessary permissions to access the database.

---

## Production Deployment
- **Production Backend (Server) Domain:** https://learnify.runasp.net/  
  (This is the same as the local server in the source code)
- **Production Frontend (Client) Domain:** https://learnify-xi-five.vercel.app/

---

## Artificial Intelligence

This project integrates two core AI subsystems to enhance user learning experience and personalization:

---

### 1. RAG System (Retrieval-Augmented Generation)

- *Purpose:* Generate dynamic and coherent learning roadmaps using semantic search and generative AI.
- *Embedding Model:* all-MiniLM-L6-v2 from HuggingFace (vector size: 384, cosine similarity).
- *Vector Store:* Qdrant for fast semantic retrieval based on indexed course metadata (category, level).
- *LLM Generator:* llama-3-70b via ChatGroq API (temperature: 0.5).
- *Use Case:* Given a user query or goal, the system retrieves relevant courses and generates a logical progression with AI-written transitions.

---

### 2. Recommendation System

- *Purpose:* Suggest personalized course recommendations using hybrid filtering.
- *Techniques Used:*
  - *Content-Based Filtering:* Based on user preferences (category/level).
  - *Collaborative Filtering:* Based on overall popularity (clicks, enrollments).
  - *Hybrid Approach:* Combines both for balance between personalization and diversity.
- *Backend:* Built with FastAPI and SQL Server (via SQLAlchemy).
- *Runtime Logic:*
  - TF-IDF for content vectors.
  - User-item matrix for popularity analysis.
- *Main Endpoint:* /recommend returns recommended courses as JSON.
- *Other Endpoints:* /health, /debug, /network-test, /test-db.

---

**For any questions or setup issues, please refer to the documentation or contact the project team.**
