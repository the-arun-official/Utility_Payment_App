🌟 UtilityPay

UtilityPay is a comprehensive Flask-based subscription and utility payment management application. It is designed to help users manage their recurring payments, track bills, and make payments online securely using Razorpay. The project focuses on security, ease of use, and modular architecture, making it ideal for learning Flask, JWT authentication, and integrating payment gateways.

✨ Features

🔐 User Authentication & Security
  🗝️ Secure login and signup using JWT access and refresh tokens.
  📧 Email OTP verification for enhanced security.
  🚫 Token blocklist to handle logout and token revocation.

💳 Subscription & Payment Management
  📅 Track current, upcoming, and past subscription payments.
  📝 Manage multiple bills and subscriptions from a single dashboard.
  💰 Online payments integration using Razorpay.
  🛠️ Admin dashboard for managing all users, transactions, and notifications.

🔔 Notifications & Reminders
  📨 Send email notifications for upcoming bills.
  🗂️ Maintain records of payment history and subscription statuses.

🖥️ Responsive Frontend
  🎨 Interactive dashboards using HTML, CSS, and JavaScript.
  ⚡ Quick actions for payments, bill viewing, and admin management.
  📊 Dynamic charts and tables for easy analytics.

🛠️ Modular & Scalable
  🧩 Structured Flask project with blueprints for authentication, user management, and payment processing.
  🚀 Easily extendable for future features like analytics, multiple payment gateways, or mobile app integration.

🖥️ Tech Stack

🔹 Backend: Flask, Flask-JWT-Extended, SQLAlchemy, Flask-Mail, Flask-Migrate  
🔹 Database: SQLite (default), easy to upgrade to PostgreSQL/MySQL  
🔹 Frontend: HTML, CSS, JavaScript  
🔹 Payment Gateway: Razorpay  
🔹 Email Service: Brevo (formerly SendinBlue)  

📁 Project Structure

utilitypay/
|
📄 main.py             # Flask application entry point
📄 auth_routes.py      # Authentication-related routes
📄 models.py           # Database models
📄 extensions.py       # Flask extensions setup (db, JWT, mail)
📄 email_utils.py      # Functions to send OTP emails
📂 templates/          # HTML templates for dashboards and pages
📂 static/             # CSS, JS, images
📄 .env                # Environment variables (API keys, secrets)
📄 requirements.txt    # Python dependencies

⚙️ Setup & Installation

1️⃣ Clone the repository
   git clone <repo-url>
   cd utilitypay

2️⃣ Create a virtual environment
   python -m venv env
   # Activate
   # Windows: env\Scripts\activate
   # Linux/Mac: source env/bin/activate

3️⃣ Install dependencies
   pip install -r requirements.txt

4️⃣ Create a .env file in the root directory
   SECRET_KEY=super_secret_key_here
   JWT_SECRET_KEY=super_jwt_secret_here
   DATABASE_URL=sqlite:///users.db
   BREVO_API_KEY=your_brevo_api_key
   MAIL_SENDER_NAME=PaySub
   MAIL_SENDER_EMAIL=your_email@example.com
   ACCESS_TOKEN_EXPIRES_MINUTES=180
   REFRESH_TOKEN_EXPIRES_DAYS=7
   FRONTEND_URL=http://localhost:5000
   PORT=5000

5️⃣ Run the Flask application
   python main.py

6️⃣ Access the application
   🌐 Open your browser and go to: http://localhost:5000/dashboard

🎓 Learning & Value

This project demonstrates the following key skills:  
🔒 Building secure Flask applications with JWT authentication.  
💳 Integrating payment gateways for real-world applications.  
📧 Implementing email notifications and OTP verification.  
🧩 Designing modular and scalable applications for production-ready deployment.  
☁️ Preparing for cloud deployment with AWS and containerization.

Even as a fresher, adding this project to my resume will showcase your full-stack skills, understanding of real-world payment systems, and readiness for professional deployment scenarios.

📄 License

This project is open-source and free to use for learning and development purposes.
