# PWP SPRING 2026
# PROJECT NAME
# Group information
* Akash Bappy
* Student 2. Name and email
* Student 3. Name and email
* Student 4. Name and email


__Remember to include all required documentation and HOWTOs, including how to create and populate the database, how to run and test the API, the url to the entrypoint, instructions on how to setup and run the client, instructions on how to setup and run the axiliary service and instructions on how to deploy the api in a production environment__



# Pi Security Camera System

A RESTful motion-detecting security camera system built with Raspberry Pi and Pi Camera, featuring automated motion detection, image capture, and a web-based viewing interface.



## Overview

This project implements a complete security camera solution that:
- Detects motion using computer vision on a Raspberry Pi
- Captures and uploads images to a REST API server
- Provides a client interface for viewing live and historical footage
- Logs all motion events with detailed metadata

### Key Capabilities

- **REST API Design**: Full CRUD operations across multiple resources
- **IoT Integration**: Raspberry Pi with Pi Camera hardware
- **Automated Monitoring**: Background service for continuous motion detection
- **Object Detection**: YOLO + COCO dataset for real-time object recognition with confidence scores
- **Web Client**: Intuitive interface for accessing motion events and images

---

## Features

### Core Functionality
- ⚡ Real-time motion detection with configurable sensitivity
- 📸 Automatic image capture and server upload
- � **Object detection using YOLOv5 + COCO dataset**
- 📊 Detailed logging of motion events with timestamps and detection data
- 🖥️ Client application for viewing live and archived footage
- 🔔 Optional alert notifications for motion events

### Technical Features
- RESTful API with resources: `/cameras`, `/images`, `/motions`, `/detections`, `/alerts`, `/users`
- Persistent storage (SQLite/JSON)
- User authentication and authorization
- Timeline visualization of motion events


## Project Architecture

```
Raspberry Pi + Pi Camera
    │
    ├─ Motion Detection
    ├─ Image Capture
    ├─ Object Detection (YOLO + COCO)
    │
    ▼ POST  /detections (class, confidence), /images, /motions, /alerts
    
REST API Server
    │
    ├─ Resources: /cameras, /images, /motions, /detections, /alerts, /users
    ├─ Database (SQLite/JSON)
    │
    ▼ GET requests
    
Client Application
    │
    ├─ View Images & Motion Events
    ├─ Manage Alerts
    └─ User Authentication
    └─ Visualize Timeline with Motion Events
```

**Components:**

1. **REST API Server**
   - Manages cameras, images, motions, alerts, and users
   - Provides RESTful endpoints for all operations
   - Handles data persistence and retrieval

2. **Client Application**
   - Web-based interface for viewing captured images
   - Timeline view of motion events
   - Alert configuration and management
   - User authentication and session handling

3. **Auxiliary Service** (Raspberry Pi)
   - Runs continuously on the Raspberry Pi
   - Monitors camera feed for motion
   - **Performs real-time object detection using YOLO and COCO dataset**
   - Captures and uploads images when motion detected
   - **Sends detected object classes and confidence scores to server**
   - Triggers alerts based on configured rules


### Object Detection Details
- Uses YOLOv5s model with COCO dataset (80 classes)
- Runs inference on Raspberry Pi (may require optimization for performance)
- Sends class names and confidence scores to server
- Images are captured and uploaded when motion + objects detected
