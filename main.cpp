#include "opencv2/core/core.hpp"
#include "opencv2/videoio.hpp"
#include "opencv2/highgui.hpp"
#include <opencv2/imgproc.hpp>
#include <iostream>
#include <unistd.h>
#include <stdio.h>
#include <fstream>
#include <string>
#include <curl/curl.h>

using namespace cv;
using namespace std;

CURL *curl;
CURLcode res;

size_t Callback(const char* in, size_t size, size_t num, std::string* out){
    const size_t totalBytes(size * num);
    out->append(in, totalBytes);
    return totalBytes;
}


int getLocation(string &data){
    const std::string url("http://ipinfo.io/json");
    CURL* curl = curl_easy_init();
    
    // Set remote URL.
    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    
    // Don't bother trying IPv6, which would increase DNS resolution time.
    curl_easy_setopt(curl, CURLOPT_IPRESOLVE, CURL_IPRESOLVE_V4);
    
    // Don't wait forever, time out after 10 seconds.
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 10);
    
    // Follow HTTP redirects if necessary.
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);

    // Response information.
    int httpCode(0);
    std::unique_ptr<std::string> httpData(new std::string());

    // Hook up data handling function.
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, Callback);

    // Hook up data container (will be passed as the last parameter to the
    // callback handling function).  Can be any pointer type, since it will
    // internally be passed as a void pointer.
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, httpData.get());

    // Run our HTTP GET command, capture the HTTP response code, and clean up.
    curl_easy_perform(curl);
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &httpCode);
    curl_easy_cleanup(curl);

    if (!(httpCode == 200))
    {
        std::cerr << "Couldn't GET from " << url << " - exiting" << std::endl;
        return 1;
    }

    data = httpData.get()->c_str();
    return 0;

}

int sendMessage(const string& data){
    curl = curl_easy_init();

    if(curl) {
        struct curl_slist *headers = NULL;
        headers = curl_slist_append(headers, "Accept: application/json");
        headers = curl_slist_append(headers, "Content-Type: application/json");
        headers = curl_slist_append(headers, "charset: utf-8");
        curl_easy_setopt(curl, CURLOPT_URL, "https://9e75-82-80-173-170.ngrok-free.app/message");
        curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, "POST");
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, data.c_str());
        curl_easy_setopt(curl, CURLOPT_USERAGENT, "libcrp/0.1");
        res = curl_easy_perform(curl);
        if(res != CURLE_OK){
        fprintf(stderr, "curl_easy_perform() failed: %s\n",
                curl_easy_strerror(res));
                return 1;
        }
        /* always cleanup */
        curl_easy_cleanup(curl);
    }
    curl_global_cleanup();
    return 0;
}

int FIRE_REPORTED = 0;

int main(int, char **)
{
    string data;
    
    Mat frame, resized, blur, hsv, mask, output;
    //--- INITIALIZE VIDEOCAPTURE
    VideoCapture cap;
    cap.open(0);

    // check if we succeeded
    if (!cap.isOpened())
    {
        cerr << "ERROR! Unable to open camera\n";
        return -1;
    }

    double fps = 10;

    namedWindow("drone-fire-detector", WINDOW_NORMAL);

    cap.set(cv::CAP_PROP_FRAME_WIDTH, 640); 
    cap.set(cv::CAP_PROP_FRAME_HEIGHT, 480);
    for (;;)
    {
        double start_time = (double)getTickCount();

        // wait for a new frame from camera and store it into 'frame'
        cap.read(frame);

        double end_time = (double)getTickCount();
        // check if we succeeded
        if (frame.empty())
        {
            cerr << "ERROR! blank frame grabbed\n";
            break;
        }
        
        resize(frame, resized, Size(960, 540));
        GaussianBlur(resized, blur, Size(21, 21), 0);
        cvtColor(blur, hsv, cv::COLOR_BGR2HSV);

        Scalar lower(0,120,120), upper(20,255,255);
        inRange(hsv, lower, upper, mask);
        bitwise_and(resized, hsv, output, mask);
        int no_red = countNonZero(mask);

        if(no_red > 15000){
            ++FIRE_REPORTED;
            getLocation(data);
            cout << data;
            sendMessage(data);
        }

        imshow("Live", frame);
        if (waitKey(5) >= 0)
            break;

        double process_time = (end_time - start_time) / cv::getTickFrequency(); 
        
        if (process_time < 1. / fps) {
            usleep(((1. / fps) - process_time)*1000000);
        }

    }
    
    return 0;
}

