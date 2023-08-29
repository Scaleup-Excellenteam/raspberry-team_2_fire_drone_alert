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

const int TIMEOUT = 10;
const int FRAME_WIDTH = 640;
const int FRAME_HEIGHT = 480;
const int RESIZED_WIDTH = 960;
const int RESIZED_HEIGHT = 540;
const Scalar LOWER_MASK(0, 120, 120);
const Scalar UPPER_MASK(20, 255, 255);
const std::string IP_INFO_URL = "http://ipinfo.io/json";
const std::string POST_URL = "https://9e75-82-80-173-170.ngrok-free.app/message";
const int FIRE_THRESHOLD = 15000;
const Size BLUR_SIZE(21, 21);
const double FPS = 10.0;
const int MICROSECONDS_IN_SECOND = 1000000;

CURL *curl;
CURLcode res;

size_t Callback(const char* in, size_t size, size_t num, std::string* out){
    const size_t totalBytes(size * num);
    out->append(in, totalBytes);
    return totalBytes;
}

int getLocation(string &data){
    CURL* curl = curl_easy_init();
    curl_easy_setopt(curl, CURLOPT_URL, IP_INFO_URL.c_str());
    curl_easy_setopt(curl, CURLOPT_IPRESOLVE, CURL_IPRESOLVE_V4);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, TIMEOUT);
    curl_easy_setopt(curl, CURLOPT_FOLLOWLOCATION, 1L);

    int httpCode(0);
    std::unique_ptr<std::string> httpData(new std::string());
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, Callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, httpData.get());
    curl_easy_perform(curl);
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &httpCode);
    curl_easy_cleanup(curl);

    if (httpCode != 200)
    {
        std::cerr << "Couldn't GET from " << IP_INFO_URL << " - exiting" << std::endl;
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
        curl_easy_setopt(curl, CURLOPT_URL, POST_URL.c_str());
        curl_easy_setopt(curl, CURLOPT_CUSTOMREQUEST, "POST");
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, data.c_str());
        curl_easy_setopt(curl, CURLOPT_USERAGENT, "libcrp/0.1");
        res = curl_easy_perform(curl);
        if(res != CURLE_OK){
            fprintf(stderr, "curl_easy_perform() failed: %s\n", curl_easy_strerror(res));
            return 1;
        }
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

    VideoCapture cap;
    cap.open(0);

    if (!cap.isOpened())
    {
        cerr << "ERROR! Unable to open camera\n";
        return -1;
    }

    namedWindow("drone-fire-detector", WINDOW_NORMAL);
    cap.set(cv::CAP_PROP_FRAME_WIDTH, FRAME_WIDTH); 
    cap.set(cv::CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT);

    for (;;)
    {
        double start_time = (double)getTickCount();
        cap.read(frame);
        double end_time = (double)getTickCount();

        if (frame.empty())
        {
            cerr << "ERROR! blank frame grabbed\n";
            break;
        }

        resize(frame, resized, Size(RESIZED_WIDTH, RESIZED_HEIGHT));
        GaussianBlur(resized, blur, BLUR_SIZE, 0);
        cvtColor(blur, hsv, cv::COLOR_BGR2HSV);
        inRange(hsv, LOWER_MASK, UPPER_MASK, mask);
        bitwise_and(resized, hsv, output, mask);
        int no_red = countNonZero(mask);

        if(no_red > FIRE_THRESHOLD)
        {
            ++FIRE_REPORTED;
            getLocation(data);
            cout << data;
            sendMessage(data);
        }

        imshow("Live", frame);
        if (waitKey(5) >= 0)
            break;

        double process_time = (end_time - start_time) / cv::getTickFrequency(); 
        if (process_time < 1. / FPS)
        {
            usleep(((1. / FPS) - process_time) * MICROSECONDS_IN_SECOND);
        }
    }
    return 0;
}
