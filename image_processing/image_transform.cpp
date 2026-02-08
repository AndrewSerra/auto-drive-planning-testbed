#include "image_transform.h"

using namespace image_transform;

cv::Mat ImageTransform::loadImage(const std::string& imagePath) {
    cv::Mat img = cv::imread(imagePath, cv::IMREAD_GRAYSCALE);
    std::cout << "Loading image: " << imagePath << std::endl;
    if(img.empty()) throw std::runtime_error("could not read image");

    return img;
}

cv::aruco::ArucoDetector ImageTransform::configureDetector() {
    cv::aruco::DetectorParameters detectorParams = cv::aruco::DetectorParameters();
    cv::aruco::Dictionary dictionary = cv::aruco::getPredefinedDictionary(cv::aruco::DICT_APRILTAG_36h11);
    return cv::aruco::ArucoDetector(dictionary, detectorParams);
}

cv::Vec3f ImageTransform::toLine(cv::Point2f a, cv::Point2f b) {
    // Homogeneous line from two points: l = a x b
    cv::Vec3f pa(a.x, a.y, 1.0f);
    cv::Vec3f pb(b.x, b.y, 1.0f);
    return pa.cross(pb);
}

cv::Point2f ImageTransform::intersect(cv::Vec3f l1, cv::Vec3f l2) {
    // Point = l1 x l2, then dehomogenize
    cv::Vec3f p = l1.cross(l2);
    return cv::Point2f(p[0] / p[2], p[1] / p[2]);
}

void ImageTransform::drawAprilTagDetections(cv::Mat img, int markerId, std::vector<cv::Point2f> markerCorners) {
    // Draw tag outline
    for(int j = 0; j < 4; j++) {
        cv::line(img, markerCorners[j], markerCorners[(j+1) % 4], cornerColor_, thickness_);
    }
    // Draw corner circles
    for(int j = 0; j < 4; j++) {
        cv::circle(img, markerCorners[j], 15, cv::Scalar(0, 0, 255), -1);
    }
    // Mark top-left corner with a red square
    int sq = 20;
    cv::Point2f tl = markerCorners[AprilTagCornerIndex::TOP_LEFT];
    cv::rectangle(img, cv::Point(tl.x - sq, tl.y - sq), cv::Point(tl.x + sq, tl.y + sq), cv::Scalar(0, 0, 255), -1);
    // Draw tag ID
    cv::Point2f center(0, 0);
    for(auto &c : markerCorners) center += c;
    center *= 0.25f;
    cv::putText(img, std::to_string(markerId), center, cv::FONT_HERSHEY_SIMPLEX, 3.0, cv::Scalar(255, 0, 0), 6);
}

ImageTransform::ImageTransform(const std::string& imagePath) : ImageTransform(loadImage(imagePath)) {
    this->imagePath_ = imagePath;
}

ImageTransform::ImageTransform(cv::Mat image) {
    this->detector_ = this->configureDetector();

    std::vector<int> markerIds;
    std::vector<std::vector<cv::Point2f>> markerCorners, rejectedCandidates;

    this->detector_.detectMarkers(image, markerCorners, markerIds, rejectedCandidates);

    std::cout << "Detected number of markers: " << markerCorners.size() << std::endl;

    float imgW = static_cast<float>(image.cols);
    float imgH = static_cast<float>(image.rows);

    std::vector<cv::Point2f> bottomMarker, topMarker;

    for(int i=0; i < markerIds.size(); i++) {
        switch(markerIds.at(i)) {
            case 0: bottomMarker = markerCorners.at(i); break;
            case 1: topMarker= markerCorners.at(i); break;
            default:
                throw std::runtime_error("unknown april tag id detected");
        }
    }

    cv::Vec3f leftEdge   = toLine(bottomMarker.at(AprilTagCornerIndex::BOTTOM_LEFT), bottomMarker.at(AprilTagCornerIndex::TOP_LEFT));
    cv::Vec3f topEdge    = toLine(topMarker.at(AprilTagCornerIndex::TOP_RIGHT), topMarker.at(AprilTagCornerIndex::TOP_LEFT));
    cv::Vec3f bottomEdge = toLine(bottomMarker.at(AprilTagCornerIndex::BOTTOM_LEFT), bottomMarker.at(AprilTagCornerIndex::BOTTOM_RIGHT));
    cv::Vec3f rightEdge  = toLine(topMarker.at(AprilTagCornerIndex::TOP_RIGHT), topMarker.at(AprilTagCornerIndex::BOTTOM_RIGHT));

    cv::Point2f topLeft     = intersect(leftEdge, topEdge);
    cv::Point2f bottomRight = intersect(bottomEdge, rightEdge);

    // 4 corners of the surface in the source image
    std::vector<cv::Point2f> transformPoints{
        topLeft,
        topMarker.at(AprilTagCornerIndex::TOP_RIGHT),       // top-right
        bottomRight,
        bottomMarker.at(AprilTagCornerIndex::BOTTOM_LEFT),    // bottom-left
    };
    // Map to output image corners
    std::vector<cv::Point2f> destinationPoints{
        {0,    0},
        {imgW, 0},
        {imgW, imgH},
        {0,    imgH},
    };

    std::cout << "Generating homography matrix..." << std::endl;
    this->transformMatrix_ = cv::findHomography(transformPoints, destinationPoints);
}

ImageTransform::~ImageTransform() {}

void ImageTransform::saveProjectedImage(std::string outputFilePath) {
    auto image = loadImage(this->imagePath_);

    float imgW = static_cast<float>(image.cols);
    float imgH = static_cast<float>(image.rows);

    cv::Mat projected = cv::Mat::zeros(imgH, imgW, CV_32FC3);
    cv::warpPerspective(image, projected, this->transformMatrix_, image.size());

    auto success = cv::imwrite(outputFilePath, projected);
    if(success) {
        std::cout << "Successfully saved output of the projected image to: " << outputFilePath << std::endl;
    } else {
        std::cout << "Unable to save output of the projected image to: " << outputFilePath << std::endl;
    }
}
