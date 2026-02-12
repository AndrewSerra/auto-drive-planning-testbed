#ifndef IMAGE_PROCESSOR_H
#define IMAGE_PROCESSOR_H

#include <opencv2/core.hpp>
#include <opencv2/imgcodecs.hpp>
#include <string>
#include <stdexcept>
#include <iostream>

class ImageProcessor {

    protected:
    static cv::Mat loadImage(const std::string& imagePath) {
        cv::Mat img = cv::imread(imagePath, cv::IMREAD_COLOR);
        std::cout << "Loading image: " << imagePath << std::endl;
        if(img.empty()) throw std::runtime_error("could not read image");

        return img;
    }

    public:
    virtual ~ImageProcessor() = default;
    virtual void saveImage(cv::Mat image, std::string outputFilePath) = 0;
};

#endif
