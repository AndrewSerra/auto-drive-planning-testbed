#include <iostream>
#include <filesystem>
#include <stdexcept>

#include <opencv2/core.hpp>
#include <opencv2/opencv.hpp>


#define EXIT_STATUS_CANNOT_LOAD 1

#define BOTTOM_LEFT_TAG_ID    0
#define TOP_RIGHT_TAG_ID      1

#define DEBUG

enum AprilTagCornerIndex {
    TOP_LEFT,
    TOP_RIGHT,
    BOTTOM_RIGHT,
    BOTTOM_LEFT
};

cv::Mat homographyMatrix;

struct TestbedBoundary {
    
    private:
    cv::Vec3f toLine(cv::Point2f a, cv::Point2f b) {
        // Homogeneous line from two points: l = a x b
        cv::Vec3f pa(a.x, a.y, 1.0f);
        cv::Vec3f pb(b.x, b.y, 1.0f);
        return pa.cross(pb);
    };

    cv::Point2f intersect(cv::Vec3f l1, cv::Vec3f l2) {
        // Point = l1 x l2, then dehomogenize
        cv::Vec3f p = l1.cross(l2);
        return cv::Point2f(p[0] / p[2], p[1] / p[2]);
    };

    public:
    cv::Point2f topLeft, topRight, bottomLeft, bottomRight;
    // TAG ID 0 -> Bottom left
    // TAG ID 1 -> Top right
    // TAG ID 2 -> Top left
    // TAG ID 3 -> Bottom right
    TestbedBoundary(std::vector<std::vector<cv::Point2f>> tagCorners, std::vector<int> tagIds) {
        int numTags = tagIds.size();
        std::cout << std::format("Detected {} april tags.", numTags) << std::endl;

        if(numTags == 1 || numTags > 4) {
            throw std::runtime_error("Number of tags should be 2, 3, or 4.");
        }

        std::vector<cv::Point2f> *tlTag = nullptr, *trTag = nullptr, *blTag = nullptr, *brTag = nullptr;

        for(int i=0; i < tagIds.size(); i++) {
            switch (tagIds.at(i)) {
                case 0: blTag = &tagCorners.at(i); break;
                case 1: trTag = &tagCorners.at(i); break;
                case 2: tlTag = &tagCorners.at(i); break;
                case 3: brTag = &tagCorners.at(i); break;
                default:
                    throw std::runtime_error(std::format("unknown april tag id found: {}", tagIds.at(i)));
            }
        }

        if(numTags == 2 && !(blTag && trTag) && !(tlTag && brTag)) {
            throw std::runtime_error("With 2 april tags, the placement should be on opposite corners.");
        }

        // Innermost corner index for each tag ID (diagonally opposite to tag position)
        constexpr int innerCorner[] = {TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT, TOP_LEFT};

        // Assign known corners directly from detected tags
        if(tlTag) this->topLeft     = (*tlTag)[innerCorner[2]];
        if(trTag) this->topRight    = (*trTag)[innerCorner[1]];
        if(blTag) this->bottomLeft  = (*blTag)[innerCorner[0]];
        if(brTag) this->bottomRight = (*brTag)[innerCorner[3]];

        // Compute missing corners via edge line intersections
        if(numTags < 4) {
            // Each tag defines two boundary edge lines from its innermost corner
            // to the two adjacent corners. edgeMap maps tag ID -> {edge1, edge2}
            // Edge indices: 0=top, 1=right, 2=bottom, 3=left
            constexpr int edgeMap[][2] = {{3, 2}, {1, 0}, {0, 3}, {2, 1}};
            cv::Vec3f edges[4];

            std::pair<std::vector<cv::Point2f>*, int> tagList[] = {
                {blTag, 0}, {trTag, 1}, {tlTag, 2}, {brTag, 3}
            };

            for(auto& [tag, id] : tagList) {
                if(!tag) continue;
                int ic = innerCorner[id];
                edges[edgeMap[id][0]] = toLine((*tag)[ic], (*tag)[(ic + 1) % 4]);
                edges[edgeMap[id][1]] = toLine((*tag)[ic], (*tag)[(ic + 3) % 4]);
            }

            if(!tlTag) this->topLeft     = intersect(edges[0], edges[3]);
            if(!trTag) this->topRight    = intersect(edges[0], edges[1]);
            if(!blTag) this->bottomLeft  = intersect(edges[2], edges[3]);
            if(!brTag) this->bottomRight = intersect(edges[2], edges[1]);
        }
    };
};

void saveImage(cv::Mat image, std::string outputFilePath) {
    auto success = cv::imwrite(outputFilePath, image);
    if(success) {
        std::cout << "Successfully saved output of the projected image to: " << outputFilePath << std::endl;
    } else {
        std::cout << "Unable to save output of the projected image to: " << outputFilePath << std::endl;
    }
}

cv::aruco::ArucoDetector configureDetector() {
    cv::aruco::DetectorParameters detectorParams = cv::aruco::DetectorParameters();
    cv::aruco::Dictionary dictionary = cv::aruco::getPredefinedDictionary(cv::aruco::DICT_APRILTAG_36h11);
    return cv::aruco::ArucoDetector(dictionary, detectorParams);
}

void drawAprilTagDetections(cv::Mat img, int markerId, std::vector<cv::Point2f> markerCorners) {
    cv::Scalar cornerColor = cv::Scalar(0, 255, 0);
    int thickness = 8;

    // Draw tag outline
    for(int j = 0; j < 4; j++) {
        cv::line(img, markerCorners[j], markerCorners[(j+1) % 4], cornerColor, thickness);
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

TestbedBoundary detectAprilTags(cv::aruco::ArucoDetector detector, cv::Mat image) {
    std::vector<int> markerIds;
    std::vector<std::vector<cv::Point2f>> markerCorners, rejectedCandidates;

    detector.detectMarkers(image, markerCorners, markerIds, rejectedCandidates);

    std::cout << "Detected number of markers: " << markerCorners.size() << std::endl;

    float imgW = static_cast<float>(image.cols);
    float imgH = static_cast<float>(image.rows);

    return TestbedBoundary(markerCorners, markerIds);
}

cv::Mat projectImage(cv::Mat image, std::array<cv::Point2f, 4> transformPoints) {
    float imgW = static_cast<float>(image.cols);
    float imgH = static_cast<float>(image.rows);

    // Map to output image corners
    std::vector<cv::Point2f> destinationPoints{
        {0,    0},
        {imgW, 0},
        {imgW, imgH},
        {0,    imgH},
    };

    homographyMatrix = cv::findHomography(transformPoints, destinationPoints);
    cv::Mat projected = cv::Mat::zeros(imgH, imgW, CV_32FC3);
    cv::warpPerspective(image, projected, homographyMatrix, image.size());
    return projected;
}

cv::Mat getBoundary(cv::Mat image) {
    cv::Scalar boundaryColorHigh = cv::Scalar(114, 255, 255);
    cv::Scalar boundaryColorLow = cv::Scalar(40, 180, 190);

    cv::Mat mask, blur;
    std::vector<std::vector<cv::Point>> contours;
    std::vector<cv::Vec4i> hierarchy;
    cv::GaussianBlur(image, blur, cv::Size(5,5), 0.5, 0.5);
    cv::inRange(blur, boundaryColorLow, boundaryColorHigh, mask);

    // Morphological close to fill small gaps, then open to remove small noise blobs
    cv::Mat kernel = cv::getStructuringElement(cv::MORPH_ELLIPSE, cv::Size(15, 15));
    cv::morphologyEx(mask, mask, cv::MORPH_CLOSE, kernel);
    cv::morphologyEx(mask, mask, cv::MORPH_OPEN, kernel);

    cv::findContours(mask, contours, hierarchy, cv::RETR_TREE, cv::CHAIN_APPROX_SIMPLE);

    // Only draw contours above a minimum area to ignore remaining noise
    double minArea = 5000.0;
    for(size_t i = 0; i < contours.size(); i++) {
        if(cv::contourArea(contours[i]) >= minArea) {
            std::vector<cv::Point> approx;
            // Epsilon controls smoothing: increase (e.g. 0.04) for more,
            // decrease (e.g. 0.01) for less. Value is a fraction of perimeter.
            double epsilon = 0.005 * cv::arcLength(contours[i], true);
            cv::approxPolyDP(contours[i], approx, epsilon, true);
            std::vector<std::vector<cv::Point>> smoothed = {approx};
            cv::drawContours(image, smoothed, 0, cv::Scalar(0, 0, 255), 10);
        }
    }

    saveImage(image, "out/boundary.jpg");
    cv::imshow("Contour", image);
    cv::waitKey(0);

    return mask;
}

int main(int argc, char* argv[]) {
    
    std::string imgPath = "/Users/andrewserra/GithubProjects/auto-planning-software-testbed/IMG_7969.JPG";
    const std::string imgOutPath = "/Users/andrewserra/GithubProjects/auto-planning-software-testbed/out";

    auto getOutputPath = [imgOutPath](std::string fileName) -> std::string {
        return std::format("{}/{}", imgOutPath, fileName);
    };

    // Loading a image for processing.
    std::cout << "Reading image file: " << imgPath << std::endl;
    cv::Mat image = cv::imread(imgPath, cv::IMREAD_COLOR);

    if(image.empty()) {
        std::cout << "Unable to load image. Exiting program." << std::endl;
        return EXIT_STATUS_CANNOT_LOAD;
    }
    std::cout << "Succesfully loaded image." << std::endl;

    // Create output path if not exists
    if (!std::filesystem::exists(imgOutPath)) {
        std::filesystem::create_directories(imgOutPath);
        std::cout << "Created output directory: " << imgOutPath << std::endl;
    }

    // Get homography matrix 
    auto detector = configureDetector();
    auto testbedBoundary = detectAprilTags(detector, image);

    #ifdef DEBUG
    std::cout << "Top left: " << testbedBoundary.topLeft << std::endl;
    std::cout << "Top right: " << testbedBoundary.topRight << std::endl;
    std::cout << "Bottom left: " << testbedBoundary.bottomLeft << std::endl;
    std::cout << "Bottom right: " << testbedBoundary.bottomRight << std::endl;
    #endif

    std::array<cv::Point2f, 4> transformPoints = {
        testbedBoundary.topLeft,
        testbedBoundary.topRight,
        testbedBoundary.bottomRight,
        testbedBoundary.bottomLeft,
    };

    auto projectedImg = projectImage(image, transformPoints);
    saveImage(projectedImg, getOutputPath("projected.jpg"));

    auto boundary = getBoundary(projectedImg);
}
