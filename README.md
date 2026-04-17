# 🍎 Apple Fruit Disease Detection System using Deep Learning

<p align="center">
  <img src="Apple_demo.png" width="700">
</p>

> An AI-powered Flask web application that detects apple fruit diseases using an EfficientNet-based CNN model with high accuracy.

---

## 🏆 Key Highlights
- ✅ Achieved **87% validation accuracy**
- 🍏 Supports **5 disease classes**
- 🤖 Built using **EfficientNet-based CNN**
- 🌐 Integrated with **Flask Web Application**
- 👥 Includes **User & Admin modules**
- 🗄️ Stores prediction **history using SQLite**

---

## 📌 Project Overview
This project is a Machine Learning-powered web application that detects diseases in apple fruits from images. Users can upload an image, and the system predicts the disease along with a confidence score.

It combines Deep Learning with a full-stack web interface, making it practical for real-world usage.

---

## 🎯 Objective / Problem Statement
Manual detection of fruit diseases is time-consuming and requires expert knowledge. This project aims to:

- Automate disease detection using AI  
- Provide early diagnosis for better crop management  
- Reduce agricultural losses  
- Make technology accessible to farmers and users  

---

## 📊 Dataset Description
The dataset was collected from multiple sources:
- Kaggle  
- Mendeley  
- Agricultural image datasets  

It contains labeled images across the following classes:
- Anthracnose  
- Black Pox  
- Black Rot  
- Healthy  
- Powdery Mildew  

---

## 🤖 Machine Learning Model

- **Model Type:** Convolutional Neural Network (CNN)  
- **Architecture:** EfficientNet  
- **Framework:** TensorFlow / Keras  
- **Training Platform:** Google Colab  
- **Input Size:** 224 × 224  
- **Model Format:** `.keras`  

---

## 📈 Model Performance

### 📌 Overall Metrics
- **Accuracy:** 87%  
- **Precision (avg):** 86%  
- **Recall (avg):** 87%  
- **F1-Score (avg):** 86%  

### 📊 Classification Report

| Class            | Precision | Recall | F1-score | Support |
|------------------|----------|--------|----------|---------|
| Anthracnose      | 66%      | 75%    | 70%      | 69      |
| Black Pox        | 97%      | 97%    | 97%      | 92      |
| Black Rot        | 82%      | 74%    | 78%      | 134     |
| Healthy          | 95%      | 94%    | 95%      | 143     |
| Powdery Mildew   | 91%      | 94%    | 92%      | 104     |

📖 **Metric Explanation:**
- **Precision:** Correctness of positive predictions  
- **Recall:** Ability to identify all relevant cases  
- **F1-Score:** Balance between precision and recall  

---

### 🔹 Confusion Matrix
<p align="center">
  <img src="Confusion_Matrix.png" width="500">
</p>

### 🔹 Training vs Validation Accuracy
<p align="center">
  <img src="Training_Validation_Accuracy.png" width="500">
</p>

### 🔹 Training vs Validation Loss
<p align="center">
  <img src="Training_validation_Loss.png" width="500">
</p>

---

## 🌐 Web Application Features

### 👤 User Features
- User Signup & Login  
- Upload apple fruit image  
- Get disease prediction with confidence score  
- View prediction history  
- Profile management  
- Logout system  

### 🧑‍💼 Admin Features
- Admin login  
- View all user predictions  
- Manage system history  
- Admin can delete records from all users' history. 
- Monitor users  

---

## 🔁 System Workflow

1. User registers or logs in  
2. Uploads apple fruit image  
3. Image is resized to **224×224** and normalized  
4. Model processes the image  
5. Disease prediction is generated  
6. Confidence score is displayed  
7. Result stored in SQLite database  
8. User can view history in dashboard  

---

## 🧪 Model Pipeline

- Input Image → Resize (224×224)  
- Preprocessing (EfficientNet)  
- Feature Extraction (CNN Layers)  
- Softmax Classification  
- Output: Disease Label + Confidence Score  

---

## 🛠️ Tech Stack

### 🔹 Frontend
- HTML  
- CSS  
- JavaScript  

### 🔹 Backend
- Python (Flask Framework)  
- SQLite Database  

### 🔹 Machine Learning
- TensorFlow / Keras  
- EfficientNet  
- NumPy  
- PIL (Image Processing)  

### 🔹 Deployment
- Google Colab (Model Training)  
- Ngrok (Public URL)  

---

## 🗄️ Database Design

### Users Table
- id  
- email  
- password  
- role (admin/user)  

### History Table
- id  
- username  
- image path  
- prediction  
- confidence  
- date  

---

## 🚀 Deployment

- Flask app runs locally  
- Ngrok used for public access  
- Model trained using Google Colab  
- `.keras` model integrated into backend  

---

## 📸 User Interface Pages

- Home Page  
- Login Page  
- Signup Page  
- Dashboard (Prediction Screen)  
- History Page  
- Profile Page  
- Admin Panel  

---

## 👤 Author

**HEMALATHA SIVAKAI**  
📧 Email: sivakavihemalatha@gmail.com  
