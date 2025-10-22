# 🩺 Chest X-Ray Classifier (COVID-19, Normal, Lung Opacity, Viral Pneumonia)

A deep learning model using Keras/TensorFlow to classify chest X-ray images into four categories: COVID-19, Normal, Lung Opacity (Non-COVID), and Viral Pneumonia. The model leverages transfer learning with InceptionV3.

Can be deployed with [Gradio](https://gradio.app/) for an interactive demo.

---

## 📌 Features

* **Data Handling:** Uses split-folders for 90/5/5 train/val/test split and ImageDataGenerator for preprocessing (resize to 224x224, RGB conversion, normalization) and training data augmentation (rotations, shifts, zoom, flips).
* **Modeling:** Employs Transfer Learning with a pre-trained InceptionV3 base (ImageNet weights). Includes an initial phase with the base frozen, followed by fine-tuning with the base unfrozen and a low learning rate (1e-5).
* **Regularization:** Uses Dropout in the classifier head and Early Stopping (patience=7, restore best weights) to prevent overfitting.
* **Evaluation:** Tracks accuracy and categorical cross-entropy loss.
* **Workflow:** Full process detailed in the covid-19-radiography.ipynb Jupyter Notebook.

---

## 📊 Dataset

This project uses the **COVID-19 Radiography Database** from Kaggle, compiled by researchers from Qatar University, University of Dhaka, and collaborators.

* **Source:** [COVID-19 Radiography Database on Kaggle](https://www.kaggle.com/datasets/preetviradiya/covid19-radiography-dataset)
* **Composition (as used in notebook):**
    * 3,616 COVID-19 images
    * 10,192 Normal images
    * 6,012 Lung Opacity images
    * 1,345 Viral Pneumonia images

## 🚀 How to Run

1.  **Clone this repository:**
    ```bash
    git clone https://github.com/ziad0ayman/COVID-19_Radiography.git
    cd COVID-19_Radiography
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  Ensure you have the trained model file (e.g., `my_model.keras`) saved in the repository (use Git LFS if needed).
4.  Run the Gradio app:
    ```bash
    python app.py
    ```
5.  Open the local URL (e.g., `http://127.0.0.1:7860`) provided by Gradio in your browser.