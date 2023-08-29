# Raspberry Pi Fire Detection Program
This Raspberry Pi program uses a camera and analyzes the frames captured to determine if there is fire in the scene. This model uses OpenCV for object detection and cURL for making HTTP requests to send alerts during fire detection.

## Prerequisites
1. Raspberry Pi with Camera Installation
2. OpenCV
3. libcurl
4. cmake

## Installation
1. Clone the repository
2. Run 'cmake .'
3. Run 'make' to compile the code

## Usage
Execute the program with:
`./drone-fire`

In case you are running into permissions issues, try modifying the permission of the executable file (`chmod +x ./program_name`).

The program, when started, uses the webcam to survey the surroundings continuously. If a potential fire detected, the program gets the location information of the device and posts it to an HTTP endpoint.

Note: The use of an ngrok link in the code is to simulate a server where notifications of detected fires are sent. Replace this link with the actual server's URL where notifications must be sent.

If location data can't be obtained or if the HTTP request fails for some reason, the corresponding error message is printed.

 recording and distributing video, depending on your jurisdiction. If you plan to use this program in a public place, it may be necessary to obtain certain permissions beforehand.
