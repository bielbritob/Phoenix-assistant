# Phoenix-assistant

**Phoenix-assistant** is a personal project created to assist in classroom task management by leveraging machine learning models and audio recognition. With a sleek and functional interface designed primarily by me, the application automates the sending of tasks and notifications to Discord channels based on specific subjects.

This project was developed for a school fair, and it integrates multiple technologies to provide an innovative and useful tool for both students and teachers.

---

## Features

- **Image Recognition**: Trained with **Teachable Machine**, the assistant can identify images and categorize them into predefined subjects.
- **Speech-to-Text**: Converts audio recordings into text, enabling voice-based task input.
- **Discord Integration**: Sends automatic messages to specific Discord channels related to the subject, using Discord's embed style for cleaner and more organized messages.
- **Intuitive Interface**: A beautiful, user-friendly interface designed with a focus on usability, created 90% by me.

---

## Demo

Here’s a preview of how the interface looks while running:

<p align="center">
    <img src="https://github.com/bielbritob/Phoenix-assistant/blob/b13c5180d6f3ad240ac98da678513f595e0934a2/phoenixgif.gif" width="70%" alt="Phoenix Assistant Interface" />
</p>


---

## Installation Guide

To get started with **Phoenix-assistant**, follow these steps:

### 1. Download the build

You can download the latest build of the project from the link below:

[Download Phoenix-assistant](https://drive.google.com/file/d/1WQKTqsBYFDRxf7YIhryYCkY-50VtcqLl/view?usp=sharing)

### 2. Extract the ZIP file

Once the ZIP file is downloaded, extract it to a location of your choice.

### 3. Configure the `discordChannels` and `discordToken`

Inside the extracted folder, navigate to the `data` folder and configure the following files:
- **discordChannels**: Define the Discord channels where the messages will be sent.
- **discordToken**: Insert your Discord bot token here to authenticate the application.

> **Note:** You can skip this step if you don’t want to send messages to Discord.

### 4. Run the Application

After configuring the necessary files, you can run the application. If everything is set up correctly, the assistant will begin its task automation!

---

## How It Works

**Phoenix-assistant** combines several cutting-edge technologies to perform its tasks efficiently:

### 1. Image Recognition (Teachable Machine)

The assistant is trained using **Google's Teachable Machine** to recognize images and trigger actions based on the detected subject. When an image is captured or uploaded, it is processed, and the corresponding action or notification is performed (for example, sending a task update to the appropriate Discord channel).

### 2. Speech-to-Text

Using the **SpeechRecognition** library, the application can transcribe audio recordings into text. This allows the user to interact with the assistant through voice commands. The transcribed text is then analyzed to trigger specific actions or tasks.

### 3. Discord Integration

The **discord.py** library is used to send messages to specific Discord channels in the form of an embed. The bot listens for specific triggers (like an image or transcribed text), and based on the subject, it sends a message to the correct Discord channel. Each message is formatted nicely with Discord's embed style.

---

## Technologies Used

- **Python**: The main programming language for backend logic and Discord API integration.
- **Teachable Machine**: For training the image recognition model.
- **SpeechRecognition**: For converting speech to text.
- **discord.py**: To interact with the Discord API and send messages to specific channels.
- **Pygame**: For creating the graphical user interface (if applicable).
- **NumPy** and **TensorFlow**: For handling the machine learning models (if you are using them for image recognition or other tasks).

---

## Example Usage

Here’s an example of how **Phoenix-assistant** works in action:

1. **Image Recognition**: 
   - You train the model with Teachable Machine, (`keras_model.h5` and `labels`) then put in the `Phoenix` folder and change the logic of the `def verify_webcam()`
      > **Note:** You can skip this step if you don’t want to do this...

2. **Voice Command**:
   - You say "Fenix", its like alexa, then u say "enviar tarefa" then "matéria", whatever...
   - The model recognizes what u say and save it to send in final to discord

3. **Discord Channel Notification**:
   - Based on the identified subject (e.g., History or Math), the assistant sends a message to the corresponding Discord channel with a neatly formatted embed message.

---

Made with ❤️ by **bielbritob**
Check out new projects on GitHub: [Phoenix-assistant GitHub](https://github.com/bielbritob)

---

### Additional Notes:
- **Troubleshooting**: If you encounter any issues with setting up the application, check the Issues tab for common problems and solutions.
