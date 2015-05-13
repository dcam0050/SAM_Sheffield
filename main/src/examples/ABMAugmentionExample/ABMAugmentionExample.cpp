/*
 *
 * Copyright (C) 2015 WYSIWYD Consortium, European Commission FP7 Project ICT-612139
 * Authors: Tobias Fischer
 * email:   t.fischer@imperial.ac.uk
 * Permission is granted to copy, distribute, and/or modify this program
 * under the terms of the GNU General Public License, version 2 or any
 * later version published by the Free Software Foundation.
 *
 * A copy of the license can be found at
 * wysiwyd/license/gpl.txt
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
 * Public License for more details
*/

#include <stdio.h>

#include <cv.h>
#include <opencv2/opencv.hpp>

#include <yarp/os/all.h>
#include <yarp/sig/all.h>
#include "ABMAugmentionExample.h"

using namespace std;
using namespace yarp::os;
using namespace yarp::sig;
using namespace yarp::math;
using namespace cv;

bool ABMAugmentionExample::configure(yarp::os::ResourceFinder &rf) {
    setName(rf.check("name", Value("ABMAugmentionExample"), "module name (string)").asString().c_str());

    // connect to ABM
    string abmName = rf.check("abm",Value("autobiographicalMemory")).asString().c_str();
    string abmLocal = "/"+getName()+"/abm:o";
    abm.open(abmLocal.c_str());
    string abmRemote = "/"+abmName+"/rpc";

    while (!Network::connect(abmLocal.c_str(),abmRemote.c_str())) {
        cout << "Waiting for connection to ABM..." << endl;
        Time::delay(1.0);
    }

    // open ports for augmented images
    augmentedImageIn.open("/" + getName() + "/augmentedImage:i");
    augmentedImageOut.open("/" + getName() + "/augmentedImage:o");

    augmentedImageIn.setStrict(true);

    // attach to rpc port
    string handlerPortName = "/" + getName() + "/rpc";

    if (!handlerPort.open(handlerPortName.c_str())) {
        cout << getName() << ": Unable to open port " << handlerPortName << endl;
        return false;
    }

    attach(handlerPort);

    return true;
}

bool ABMAugmentionExample::respond(const Bottle& bCommand, Bottle& bReply) {
    if (bCommand.get(0).asString() == "augmentImages" )
    {
        if(bCommand.size() == 2 && bCommand.get(1).isInt()) {
            int instance = (atoi((bCommand.get(1)).toString().c_str()));
            if(receiveImages(instance)) {
                bReply.addString("[augmentImages]: Successful");
            }
        } else {
            bReply.addString("[augmentImages]: wrong function signature: augmentImages instance");
        }
        bReply.addString("ack");
    }
    else
    {
        bReply.addString("nack");
    }
    return true;
}

bool ABMAugmentionExample::receiveImages(int instance) {
    // find out how many images are saved for a specific instance
    Bottle bCmdImagesInfo, bRespImagesInfo;
    bCmdImagesInfo.addString("triggerStreaming");
    bCmdImagesInfo.addInt(instance);
    Bottle bIncludeAugmented;
    bIncludeAugmented.addString("includeAugmented");
    bIncludeAugmented.addInt(0);
    bCmdImagesInfo.addList() = bIncludeAugmented;
    Bottle bRealtime;
    bRealtime.addString("realtime");
    bRealtime.addInt(0);
    bCmdImagesInfo.addList() = bRealtime;

    yDebug() << "Send command: " << bCmdImagesInfo.toString();
    abm.write(bCmdImagesInfo, bRespImagesInfo);
    yDebug() << "Got reply: " << bRespImagesInfo.toString();

    vRawImages.clear();
    vEnvelopes.clear();
    vAugmentedImages.clear();

    int numberOfImages=0;
    string portName = "/autobiographicalMemory/icub/camcalib/right/out";

    Bottle* bListImgProviders = bRespImagesInfo.get(2).asList();
    for(int i=0; i<bListImgProviders->size(); i++) {
        if(bListImgProviders->get(i).asList()->get(0).asString()==portName) {
            numberOfImages = bListImgProviders->get(i).asList()->get(1).asInt();
        }
    }
    yDebug() << "Num images: " << numberOfImages;

    while(!Network::isConnected(portName, augmentedImageIn.getName())) {
        Network::connect(portName, augmentedImageIn.getName(), "tcp");
        yarp::os::Time::delay(0.2);
        yInfo() << "Trying to connect " << portName << " and " << augmentedImageIn.getName();
    }

    if(numberOfImages>0) {
        // now, get images frame by frame
        for(int image_number=0; image_number<numberOfImages; image_number++) {
            yInfo() << "Receive image with image number: " << image_number;
            yarp::sig::ImageOf<yarp::sig::PixelRgb> *image = augmentedImageIn.read();
            if(image!=NULL) {
                Bottle env;
                augmentedImageIn.getEnvelope(env);
                yDebug() << "Received envelope: " << env.toString();

                vRawImages.push_back(image);
                vEnvelopes.push_back(env);
            } else {
                yError() << "Did not receive image!";
            }
        }

        augmentImages();
        sendAugmentedImages();

        return true;
    } else {
        return false;
    }
}

void ABMAugmentionExample::augmentImages() {
    yInfo() << "Going to augment images";
    yAssert(vRawImages.size()==vEnvelopes.size());

    for(size_t i = 0; i<vRawImages.size(); i++) {
        IplImage *rawImageIpl = cvCreateImage(cvSize(vRawImages[i]->width(), vRawImages[i]->height()), IPL_DEPTH_8U, 3);
        cvCvtColor((IplImage*)vRawImages[i]->getIplImage(), rawImageIpl, CV_RGB2BGR);
        Mat myImage(rawImageIpl);

        // here, do Canny edge detection as example
        Mat myImage_gray;
        cvtColor( myImage, myImage_gray, CV_BGR2GRAY );
        int lowThreshold = 20;
        int ratio = 3;
        int kernel_size = 3;
        Canny( myImage_gray, myImage_gray, lowThreshold, lowThreshold*ratio, kernel_size );
        Mat augmented;
        augmented.create( myImage.size(), myImage.type() );
        augmented = Scalar::all(0);
        myImage.copyTo( augmented, myImage_gray);

        //imshow("Canny", augmented);
        //waitKey(0);

        // convert back to IplImage
        IplImage augmentedImageIpl = augmented;
        // end your stuff
        // from IplImage to yarp image
        cvCvtColor(&augmentedImageIpl, &augmentedImageIpl, CV_BGR2RGB);
        ImageOf<PixelRgb> augmentedImageYarp;
        augmentedImageYarp.resize(augmentedImageIpl.width, augmentedImageIpl.height);
        cvCopyImage(&augmentedImageIpl, (IplImage *)augmentedImageYarp.getIplImage());
        vAugmentedImages.push_back(augmentedImageYarp);

        cvReleaseImage(&rawImageIpl);
    }
}

void ABMAugmentionExample::sendAugmentedImages() {
    yInfo() << "Going to send augmented images to ABM";
    yAssert(vAugmentedImages.size()==vEnvelopes.size());

    while(!Network::isConnected(augmentedImageOut.getName(), "/autobiographicalMemory/augmented:i")) {
        Network::connect(augmentedImageOut.getName(), "/autobiographicalMemory/augmented:i", "tcp");
        yarp::os::Time::delay(0.2);
        yInfo() << "Trying to connect " << augmentedImageOut.getName() << " and " << "/autobiographicalMemory/augmented:i";
    }
    yDebug() << "Ports connected";

    string augmentedLabel = "Canny";

    for(size_t i = 0; i<vAugmentedImages.size(); i++) {
        yarp::sig::ImageOf<yarp::sig::PixelRgb>& currImage = augmentedImageOut.prepare();
        currImage = vAugmentedImages[i];
        vEnvelopes[i].addString(augmentedLabel);
        augmentedImageOut.setEnvelope(vEnvelopes[i]);
        yDebug() << "Send image with envelope " << vEnvelopes[i].toString();
        augmentedImageOut.writeStrict();
    }
    augmentedImageOut.waitForWrite();

    Network::disconnect(augmentedImageOut.getName(), "/autobiographicalMemory/augmented:i");
}

double ABMAugmentionExample::getPeriod() {
    return 0.1;
}


bool ABMAugmentionExample::updateModule() {
    return true;
}

bool ABMAugmentionExample::interruptModule() {
    augmentedImageIn.interrupt();
    augmentedImageOut.interrupt();

    abm.interrupt();
    handlerPort.interrupt();

    return true;
}

bool ABMAugmentionExample::close() {
    augmentedImageIn.interrupt();
    augmentedImageIn.close();
    augmentedImageOut.interrupt();
    augmentedImageOut.close();

    abm.interrupt();
    abm.close();

    handlerPort.interrupt();
    handlerPort.close();

    return true;
}
