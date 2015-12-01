% ==========================================================================
% Copyright (C) 2014 WYSIWYD Consortium, European Commission FP7 Project ICT-612139
% Authors: Hyung Jin Chang
% email:   (hj.chang@imperial.ac.uk)
% Permission is granted to copy, distribute, and/or modify this program
% under the terms of the GNU General Public License, version 2 or any
% later version published by the Free Software Foundation.
%
% A copy of the license can be found at
% wysiwyd/license/gpl.txt
%
% This program is distributed in the hope that it will be useful, but
% WITHOUT ANY WARRANTY; without even the implied warranty of
% MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
% Public License for more details
%
% This is a main code of kinematic structure learning from YARP ABM inputs
% Triggering this module through YARP
% ==========================================================================

clc
close all
clear all

%%
%=========================================================
% add path
%=========================================================
addpath(genpath('../../include/include_Matlab'));   % add path of libraries
addpath(genpath('submodule'));     % add path of required submodules

%%
control_params;

%%
%=========================================================
% YARP port
%=========================================================
LoadYarp;
import yarp.Port;
import yarp.RpcServer;
import yarp.BufferedPortImageRgb
import yarp.Bottle
import yarp.Time
import yarp.ImageRgb
import yarp.Image
import yarp.PixelRgb
import yarp.Network

shouldClose = false;

portTrigger = Port;
portTrigger.close;

disp('Going to open port /matlab/kinematicStructure/rpc');
portTrigger.open('/matlab/kinematicStructure/rpc');

disp('=================================================================================================');
disp('- Kinematic structure extraction');
disp('>>>> Enter ''startStructureLearning #num_instance [left or right camera] [first frame] [last frame]''');
disp(' ');
disp('- Finding kinematic structure correspondences between two data');
disp('>>>> Enter ''findCorrespondence #num_instance [left or right or kinect] #num_instance [left or right or kinect]''');
disp(' ');
disp('- The module closes when ''quit'' is received');
disp('=================================================================================================');

bCommand = yarp.Bottle;
bCommand.clear();
bReply = yarp.Bottle;
bReply.clear();

%%
%=========================================================
% YARP Trigger
%=========================================================
while(~shouldClose)
    %%
    disp(sprintf('\n'))
    disp('Waiting for command...');
    portTrigger.read(bCommand, true);
    
    disp(bCommand);
    %%
    %----------------------------------------------------------------------
    if (all(isletter(bCommand.get(0))))
        if (strcmp(bCommand.get(0).toString, 'quit') || strcmp(bCommand.get(0).toString, 'close'))
            bReply.addString('[ACK. Kinematic structure module is closed.]');
            shouldClose = true;
            
            %----------------------------------------------------------------------
        elseif (strcmp(bCommand.get(0).toString, 'startStructureLearning'))     % kinematic structure learning from one video
            %%
            %=========================================================
            % YARP instruction
            %=========================================================
            instance_num = num2str(char(bCommand.get(1).toString));
            
            % get camera selection (left or right) [default: left]
            camera_selection = char(bCommand.get(2).toString);
            if(isempty(camera_selection))
                camera_selection = 'left';
            end
            
            % get starting frame index[default: 1]
            start_frame_idx = str2num(char(bCommand.get(3).toString));
            if(isempty(start_frame_idx))
                start_frame_idx = 1;
            end
            
            % get last frame index [default: last frame]
            last_frame_idx = str2num(char(bCommand.get(4).toString));
            if(isempty(last_frame_idx))
                last_frame_idx = 'last';
            end
            
            disp(['Start structure learning from ABM #',instance_num, ' using ', ...
                camera_selection,' camera, ',...
                'from frame #',num2str(start_frame_idx), ' to #', num2str(last_frame_idx)]);
            disp(sprintf('\n'))
            
            %%
            %=========================================================
            % video input selection
            %=========================================================
            disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
            videoName = 'YARP';
            disp(['Loading images from ',videoName]);
            
            %%
            %=========================================================
            % video load
            % -- feature extraction
            % ---- saving feature values
            %=========================================================
            submodule_video_loading_feature_extraction;
            
            %%
            %=========================================================
            % converting feature data to y
            %=========================================================
            [y, W, frames, points] = submodule_cvuKltRead([pwd,'/points/',filename(1:end-4),'/point_seq_%d.txt'], 1, nFrames, 'workspace', points_total);
            
            %             %%
            %             %=========================================================
            %             % background subtraction
            %             %=========================================================
            %             submodule_bg_removal;
            %             W = W_fg;
            %             y = y_fg;
            
            %%
            %=========================================================
            % main algorithm
            %=========================================================
            disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
            submodule_motion_segmentation;
            %%
            %=========================================================
            % output display
            % YARP ABM save
            %=========================================================
            submodule_display_save_structure;
            wrapper_YARP_ABM_save;
            
            bReply.addString('ack');
            bReply.addString(['Structure learning from ABM #',instance_num, ' is completed!']);
            
            %----------------------------------------------------------------------            
        elseif (strcmp(bCommand.get(0).toString, 'findCorrespondence'))
            %% kinematic structure correspondences matching from two videos
            %=========================================================
            % YARP instruction
            %=========================================================
            % Information for data P
            instance_num_P = num2str(char(bCommand.get(1).toString));
            
            % get camera selection (camcalib/left, camcalib/right, kinect)
            data_source_P = char(bCommand.get(2).toString);
            if(strcmp(data_source_P, 'left'))
                data_source_P = 'left';
            elseif(strcmp(data_source_P, 'right'))
                data_source_P = 'right';
            elseif(strcmp(data_source_P, 'kinect'))
                data_source_P = 'kinect';
            end
            
            %---------------------------------------------------------
            % Information for data Q
            instance_num_Q = num2str(char(bCommand.get(3).toString));
            
            % get camera selection (camcalib/left, camcalib/right, kinect)
            data_source_Q = char(bCommand.get(4).toString);
            if(strcmp(data_source_Q, 'left'))
                data_source_Q = 'left';
            elseif(strcmp(data_source_Q, 'right'))
                data_source_Q = 'right';
            elseif(strcmp(data_source_Q, 'kinect'))
                data_source_Q = 'kinect';
            end
            
            %---------------------------------------------------------
            disp('Finding Kinematic Structure Correspondences between ');
            disp(['ABM #',instance_num_P, ' using ', ...
                data_source_P,' camera']);
            disp(['ABM #',instance_num_Q, ' using ', ...
                data_source_Q,' camera']);
            disp(sprintf('\n'))
            
            %%
            %=========================================================
            % video input selection
            %=========================================================
            disp('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++');
            disp(['Loading data from ABM']);
            wrapper_YARP_ABM_retrieve_for_Correspondence;
            
            %%
            %=========================================================
            % 1. video load
            % -- feature extraction
            % ---- saving feature values
            % ------ converting feature data to y
            % 2. Kinematic structure generation
            %=========================================================
            if strcmp(data_source_P,'left') || strcmp(data_source_P,'right')
                idx = 'P';
                cdata_P = featureExtractionYARP(idx);
                [y_P, W_P, frames_P, points_P] = submodule_cvuKltRead([pwd,'/points/',cdata_P.filename(1:end-4),'/point_seq_%d.txt'], 1, cdata_P.nFrames, 'workspace', cdata_P.points_total);
                KineStruct_P = genKineStruct(y_P, numOfSegments_P, cdata_P, ctrl_param);
            elseif strcmp(data_source_P,'kinect')
                idx = 'P';
                KineStruct_P = genKineStruct_Kinect(idx);
            end
            
            if strcmp(data_source_Q,'left') || strcmp(data_source_Q,'right')
                idx = 'Q';
                cdata_Q = featureExtractionYARP(idx);
                [y_Q, W_Q, frames_Q, points_Q] = submodule_cvuKltRead([pwd,'/points/',cdata_Q.filename(1:end-4),'/point_seq_%d.txt'], 1, cdata_Q.nFrames, 'workspace', cdata_Q.points_total);
                KineStruct_Q = genKineStruct(y_Q, numOfSegments_Q, cdata_Q, ctrl_param);
            elseif strcmp(data_source_Q,'kinect')
                idx = 'Q';
                KineStruct_Q = genKineStruct_Kinect(idx);
            end
            
            if KineStruct_P.num_seg > KineStruct_Q.num_seg
                submodule_swiping_KineStruct;
            end
            
            %%
            %=========================================================
            % Calculate Similarity
            %=========================================================
            %(1:HGM / 2:TM / 3:RRWHM / 4:BCAGM / 5:BCAGM+MP / 6:BCAGM+IPFP / 7:MPM / 8:RRWM / 9:IPFP / 10:SM)
            HGM_method = 3;
            %%
            if HGM_method <= 3
                problem = createSimilarity_RRWHM_relative(KineStruct_P, KineStruct_Q);
            elseif HGM_method == 4 || HGM_method == 5 || HGM_method == 6
                problem = createSimilarity_BCAGM(KineStruct_P, KineStruct_Q);
            end
            
            %%
            %=========================================================
            % Hypergraph Matching
            %=========================================================
            setAlg;
            % Alg(HGM_method).bOrder = [1 0 0];   % 1st
            % Alg(HGM_method).bOrder = [0 1 0];   % 2nd
            % Alg(HGM_method).bOrder = [0 0 1];   % 3rd
            % Alg(HGM_method).bOrder = [1 1 1];   % all
            
            X = hyperGraphMatching(problem, HGM_method, Alg);
            
            figure(98); imagesc(X);
            
            %%
            %=========================================================
            % Draw Matching Result
            %=========================================================
            img_output = genMatchImages(cdata_P, cdata_Q, KineStruct_P, KineStruct_Q, data_source_P, data_source_Q, X, 'PROPOSED_RRWHM');
            
            %%
            %=========================================================            
            % output display
            % YARP ABM save
            %=========================================================            
            wrapper_YARP_ABM_save_for_Correspondence;
            
            bReply.addString('ack');
            bReply.addString(['Finding Kinematic Structure Correspondences between ABM #', instance_num_P, ' and ABM #', instance_num_Q,' is completed!']);
            
            %----------------------------------------------------------------------
        else
            disp('Command not understood!');
            bReply.addString('Command not understood!');
        end
    else
        disp('Wrong input bottle format!');
        bReply.addString('Wrong input bottle format!');
    end
    
    portTrigger.reply(bReply);
    bReply.clear();
end

%%
% Module close
portTrigger.close;