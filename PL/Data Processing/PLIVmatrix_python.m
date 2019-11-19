function [M,N,datastruc]=PLIVmatrix_python(datastruc,cellarea)
% Function creating the matrix necessary for extraction of PLIV parameters
% Uses the new file format from Sept 2019 where data is saved in an h5py
% file and each line of the structure array corresponds to different
% (V,suns) measurement conditions.
% datastruc is a structure containing the EL and PL data FOR ONE SAMPLE
% ONLY

% Constants
k=1.38e-23; % J/K
qC=1.6022e-19; % C
T=298.14; % K
VT=k*T/qC;
%area=9e-4; % Cell area (m²)

%Jscindex=2; % index of the image taken at Jsc (for image correction)

picstart=12; % Start at an image that does not have negative values after Jsc correction

% Definition of known matrices and vectors
% Each line of M contains the parameters of the equation at a given voltage
% and laser intensity
M=cell(size(datastruc(1).image_bgc)); % M contains the matrices corresponding to each pixel (so the cell has the same size as the images)
N=cell(size(datastruc(1).image_bgc));

L=length(datastruc); % Number of measurements taken

% Find number of voltage values and intensity values used in the PLIV
% measurements
k=2;
while(datastruc(k+1).set_voltage > datastruc(k).set_voltage) % find the list of voltage values
   k=k+1;
end
% nb_V=k-2; % Number of voltage values (the two first images are correction images at Voc (not at Jsc!!)
nb_V=k-1; % If filtering images containing 'PLIV' in the notes, the first image in the structure is at Voc and the rest are regular images
nb_int=(L-1)/nb_V; % Number of laser intensity values

% Correct each image with the image at short-circuit and define array
% containing index of Jsc map corresponding to each measurement
Jscindex=zeros(L,1);
% All data except first image (Voc at 1 sun, corrected in the main script)
for i=2:L
    %     datastruc(i).netimage=datastruc(i).image_bgc-datastruc(i).intensity*(datastruc(Jscindex).image_bgc-datastruc(1).image_bgc); % Calculate net images by subtracting short-circuit image % The 1 sun short-circuit value is in the second line of the datastruc array
    Jscindex(i)=nb_V*floor((i-2)/nb_V)+2 ; % Index of the Jsc map at the intensity corresponding to index i
    datastruc(i).Jscindex=Jscindex(i); % Save in a new field in the structure
    datastruc(i).netimage=datastruc(i).image_bgc-datastruc(Jscindex(i)).image_bgc; % Subtract map at Jsc and at intensity corresponding to index i
end

%{
%% Save 1 sun Jsc images rescaled with light intensity
intarray=[];
% obtain array of intensity values
% for i=3:L
for i=2:L % for all images (except the first image that is at Jsc), make array of intensity values
    intarray=[intarray,datastruc(i).intensity];
end
int_reshaped=reshape(intarray,nb_V,nb_int);

% Save sun-rescaled Jsc image at the indices of each corresponding intensity
for i=1:nb_int
    datastruc(nb_V*(i-1)+3).Jsc_1sunRescaled=int_reshaped(1,i)*(datastruc(Jscindex).image_bgc-datastruc(1).image_bgc); % phi=Isun*phi_Jsc1sun where Isun is a fraction of 1 sun
end
%}

close all;
%% Plot images
% sq=ceil(sqrt(L)); % Calculate appropriate size for subplot

% Plot two first Jsc correction images
PLIVplot(datastruc, nb_V, nb_int, 1, 1); % net image, Voc and 1 sun
PLIVplot(datastruc, nb_V, nb_int, 2, 1); % bgc image, Voc and 1 sun

% Plot PLIV images at different conditions
% for i=3:L
for i=2:L % for all images (except the first image that is at Voc), make array of intensity values
    % Net background-corrected images (Jsc subtracted)
    f1=figure(1);
    subplot(nb_int+1,nb_V,i+nb_V-1); % Plot Voc image in the first row, then PLIV images at different conditions in next row
%     set(f1,'Visible','off');
    imagesc(datastruc(i).netimage);
    c=colorbar; % Plot net images
    c.FontSize=11;
    I=datastruc(i).current;
    V=datastruc(i).set_voltage;
    int=datastruc(i).intensity;
    title_str=sprintf('%2.0f mV, %.1f sun, %2.0f mA',V*1e3,int,I*1e3);
    title(title_str,'FontSize',11);
    % Raw background-corrected images (before Jsc subtration)
    f2=figure(2);
    subplot(nb_int+1,nb_V,i+nb_V-1);
%     set(f2,'Visible','off');
    imagesc(datastruc(i).image_bgc); % Plot background corrected images before Jsc correction
    c=colorbar; % Plot net images
    c.FontSize=11;
    I=datastruc(i).current;
    V=datastruc(i).set_voltage;
    int=datastruc(i).intensity;
    title_str=sprintf('%2.0f mV, %.1f sun, %2.0f mA',V*1e3,int,I*1e3);
    title(title_str,'FontSize',11); %annotation('textbox','string',title_str);  
end

%{
% Rescaled Jsc images based on laser intensity
figure(3)
for i=1:nb_int
    subplot(nb_int,1,i);
    imagesc(datastruc(nb_V*(i-1)+3).Jsc_1sunRescaled);
    c=colorbar;
    c.FontSize=11;
    int=datastruc(nb_V*(i-1)+3).intensity;
    title_str=sprintf('Rescaled 1-sun Jsc image at %.1f sun',int);
    title(title_str,'FontSize',11);
    hold on
end
hold off
%}

% Mask value where the set voltage is 0 (Jsc and Voc values)



%% Create the matrix to solve the system of equations for each pixel
% For each pixel, create a matrix M of known input parameters and input
% initial values for the unknown vector X to find. The equation to solve is
% MX=N.
picend=length(datastruc);
k=0;
count=1;
for i=picstart:picend % i corresponds to each image at different voltages % Need to skip Jsc images
    if(datastruc(i).set_voltage==0)
        realJscRow(count)=i-picstart+1; % real indices of the Jsc rows in the matrix (to be removed at the end).
        JscRowMask(count)=realJscRow(count)-count+1; % Count added to offset the line each time a Jsc measurement is found (to later remove the line in the matrix)
        count=count+1;
    end
    for p=1:size(datastruc(i).netimage,1) 
        for q=1:size(datastruc(i).netimage,2) % For all pixel columns
            %         for p=120:160 % For all pixel lines (take only a small portion of the image, make sure this is within the cell)
            %             for q=120:160 % For all pixel columns
            % M{p,q} is the matrix corresponding to each pixel
            M{p,q}(i-picstart+1+k,1)= 1; % the first column is always 1
            %             M{p,q}(i-picstart,2)= -datastruc.PLIV(i).bias.currentmeas/area; % Current density Jlight corresponding to the image (A/m²). WRONG EXPRESSION!! This should be Jsc, thus the same for all images as they are at the same illumination!
            M{p,q}(i-picstart+1+k,2)= datastruc(i).intensity*datastruc(Jscindex(i)).current/cellarea; % Light-generated current found from the measurement in short-circuit (A/m²).
            M{p,q}(i-picstart+1+k,3)= datastruc(i).netimage(p,q); % Net photon flux phi_net at the pixel, ie simply the PL intensity corrected by the image at short-circuit
            M{p,q}(i-picstart+1+k,4)= sqrt(datastruc(i).netimage(p,q)); % squareroot of the net photon flux
            % N{p,q} is the solution vector corresponding to each pixel
            N{p,q}(i-picstart+1+k,1)=VT*log(datastruc(i).netimage(p,q))-datastruc(i).voltage; % VT*ln(phi_net)-Vterm         
        end
    end
end
%k=k+picend-picstart+1; % number of lines to add to the matrix to enter the next parameters for an image at different intensity
    %(eg: picstart=2 for a total of 9 images at different voltages, meaning

% Remove lines generated from Jsc maps
for ii=1:length(JscRowMask)
    for p=1:size(datastruc(end).netimage,1) 
        for q=1:size(datastruc(end).netimage,2) % For all pixel columns
            M{p,q}(JscRowMask(ii),:)=[]; % Remove Jsc line
            N{p,q}(JscRowMask(ii),:)=[];
        end
    end
end   

disp('matrix ready');