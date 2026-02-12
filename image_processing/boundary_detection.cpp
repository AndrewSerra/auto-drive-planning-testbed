#include "boundary_detection.h"

using namespace image_transform;

BoundaryDetection::BoundaryDetection(const std::string& imagePath) {
    this->imagePath_ = imagePath;
}

BoundaryDetection::~BoundaryDetection() {}

cv::Mat BoundaryDetection::getBoundary(cv::Mat image) {
    cv::Mat mask = image.clone();
    std::vector<std::vector<cv::Point>> contours;
    std::vector<cv::Vec4i> hierarchy;
    cv::inRange(image, this->boundaryColorLow_, this->boundaryColorHigh_, mask);
    cv::findContours(mask, contours, hierarchy, cv::RETR_TREE, cv::CHAIN_APPROX_SIMPLE);

    cv::Mat contourImg = image.clone();
    std::vector<std::vector<cv::Point>> hulls(contours.size());
    for(size_t i = 0; i < contours.size(); i++) {
        cv::convexHull(contours[i], hulls[i]);
    }
    cv::drawContours(contourImg, hulls, -1, cv::Scalar(0, 0, 255), 10);
    cv::imshow("Contour", contourImg);
    cv::waitKey(0);
    
    return mask;
}

cv::Mat BoundaryDetection::getBoundary(const std::string& imagePath) {
    cv::Mat image = BoundaryDetection::loadImage(imagePath);
    return this->getBoundary(image);
}

void BoundaryDetection::saveImage(cv::Mat image, std::string outputFilePath) {
    auto mask = this->getBoundary(image);
    auto success = cv::imwrite(outputFilePath, mask);
    if(success) {
        std::cout << "Successfully saved output of the projected image to: " << outputFilePath << std::endl;
    } else {
        std::cout << "Unable to save output of the projected image to: " << outputFilePath << std::endl;
    }
}
