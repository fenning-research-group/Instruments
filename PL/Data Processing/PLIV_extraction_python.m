% PLIV_extraction_python
% 10/9/2019
% Extraction of solar cell parameters from PLIV images at different
% voltages AND different laser intensities from an h5py file.

% add to path folders containing general processing functions
%addpath('G:\My Drive\Scripts\Utilities');
%addpath('G:\My Drive\Scripts\Utilities\export_fig');
%addpath('G:\My Drive\PVRD2 WaRM\Experiments\FLIR PL-EL Setup\Matlab');
%addpath('G:\My Drive\Scripts\Colormaps');

% Constants
k=1.38e-23; % J/K
qC=1.6022e-19; % C
T=298.14; % K
VT=k*T/qC;
cellarea=(2*2.52^2)*1e-4; % Cell area (m²)

% folder='G:\Shared drives\FenningLab2\groupMembers\Guillaume\PLIVtest_newsetup';
folder='C:\Users\Guillaume\Documents\#UCSD\2_PVRD2_water_degradation\Results\PLIV_tests\GG_Al_10_test_10-17-2019';
% file='frgPL_20191009_0002_Test_GG_Al_10_PLIV.h5';
file='frgPL_20191017_0001_Test_GG_Al_10_PLIV_old_diffuser_new_filter.h5';

filepath=fullfile(folder,file);

%% Load data
% %{
meascurr=h5read(filepath,'/data/i'); % Measured current
measvolt=h5read(filepath,'/data/v'); % Measured voltage
maps=h5read(filepath,'/data/image_bgc'); % PL maps after background correction
intensity=h5read(filepath,'/settings/suns'); % Intensity data obtained from the calibration based on measure Jsc
set_voltage=h5read(filepath,'/settings/vbias') ; % Voltage set for each measurement

%{
% To look at the raw data
voltreshape=reshape(measvolt(3:end),5,4); % for 5 different voltage and 4
intensities
%}

% note regarding the structure of the data in h5 file:
% - the first map is taken at V=0 and intensity=0, used as a baseline for
%   all images
% - the second maps is taken at V=0 and intensity = 1 sun
% - other images are taken at different voltages and light intensities

% Organize data into a structure
% The structure lumstruc is a structure array containing a set of (voltage,illumination)
% condition at each index i. The field 'netimage' is the image corrected by
% subtracting the short-circuit image
L=length(measvolt); % number of measurements (at different voltages and intensities)
lumstruc=struct('voltage',zeros(L,1),'current',zeros(L,1),'intensity',zeros(L,1),'image_bgc',size(maps(:,:,1)),'netimage',size(maps(:,:,1)),'set_voltage',zeros(L,1)); % Preallocate structure
for i=1:L
    lumstruc(i).voltage=measvolt(i);        % Voltage measured from Kepco
    lumstruc(i).current=meascurr(i);        % Current measured from Kepco
    lumstruc(i).intensity=intensity(i);     % Light intensity measured based on the calibration curve of the detector
    lumstruc(i).image_bgc=maps(:,:,i);      % Image corrected using background image
    lumstruc(i).set_voltage=set_voltage(i); % Voltage setpoint on the Kepco
end
    
% %}

% Initialize vectors
% Solution vector
X=cell(size(lumstruc(1).image_bgc)); % Size of the first map
% Calculated parameters
Rs=zeros(size(lumstruc(1).image_bgc));
J01=zeros(size(lumstruc(1).image_bgc));
J02=zeros(size(lumstruc(1).image_bgc));
Voc1sun=zeros(size(lumstruc(1).image_bgc));
Jmpp1sun=zeros(size(lumstruc(1).image_bgc));
Vmpp1sun=zeros(size(lumstruc(1).image_bgc));
C=zeros(size(lumstruc(1).image_bgc));
% The images are found as lumstruc.PLIV(i).image.mean;

% Calculate resistance
% GB2=PLIVmatrix(GB2);
[M,N,lumstruc]=PLIVmatrix_python(lumstruc,cellarea); % Need to add arguments here to select which images to use

%% Calculate parameter maps
% plotPLIV_intensities(GB2,folder,'GB2');
%plotPLIV_intensities(GG8,folder,'GG8');

%{
% Plot all net images being used
for j=1:3:length(GB2)
    for i=1:length(GB2(j).PLIV)
        figure(j);
        subplot(2,5,i);
        imagesc(GB2(j).PLIV(i).netimage);
        titletxt=sprintf('V = %s',num2str(GB2(j).PLIV(i).bias.voltagemeas));
        title(titletxt);
        colorbar
    end
    imagetitletxt=sprintf('Jsc-corrected images for I= %s A',num2str(GB2(j).lasercurrent));
    sgtitle(imagetitletxt);
end
%}


% Find image at 1 sun and Vmpp conditions.
% Note that the 3rd PLIV point is at Vmpp -- for instance
% lumstruc(3).voltage if there are no EL measurements in the file.
mpp1sun=0;
for ii=1:L
    if(lumstruc(ii).intensity==1 && lumstruc(ii).voltage==lumstruc(3).voltage) % NOTE: to change if there is EL data in the h5py file (number of EL maps + 3 instead of 3)
        mpp1sun=ii; % Point at 1 sun and at max power point voltage
    end    
end

% Display warning if the 1 sun max power point was not found
if(mpp1sun==0)
    warn_str=['No 1 sun max power point conditions found, using instead'...
        'conditions at 1 sun and short-circuit'];
    warning(warn_str);
    mpp1sun=2; % Corresponds to data at 1 sun and 0 V (NOTE: to change if there is EL data in the h5py file: number of EL maps + 2 instead of 2)
end


for p=1:size(M,1) % For all pixel columns
    for q=1:size(M,2) % For all pixel lines
        % X{p,q}=M{p,q}\N{p,q};
        X{p,q}=linsolve(M{p,q},N{p,q});
        Rs(p,q)=X{p,q}(2); % The Rs value is in the second element of vector X
        C(p,q)=exp(X{p,q}(1)/VT);
%         J01(p,q)=-X{p,q}(3)*C(p,q)/Rs(p,q);
%         J02(p,q)=-X{p,q}(4)*sqrt(C(p,q))/Rs(p,q);
%         Voc1sun(p,q)= VT*log((GG8(4).PLIV(8).image.mean(p,q)-GG8(4).PLIV(2).image.mean(p,q))/C(p,q));
%         % Local voltage Vxy for the measurements close to 1 sun (0.905 A
%         current). Based on the measurement from % and to open circuit
        Vmpp1sun(p,q)=VT*log(lumstruc(mpp1sun).netimage(p,q)/C(p,q)); % V % lumstruc(3) contains data at maximum powerpoint and 1 sun (WRONG!!!)
%         Jmpp1sun(p,q)=-J01(p,q)*(exp(Vmpp1sun(p,q)/VT)-1)-J02(p,q)*(exp(Vmpp1sun(p,q)/(2*VT))-1)+GG8(4).PLIV(2).bias.currentmeas/area; % A/m²
    end
end

% Replace all complex values by NaN
Rs_real=Rs;
Rs_real(imag(Rs_real)~=0)=NaN;

% Final series resistance in Ohm-cm²
Rs_final=-Rs_real*1e4;


% Process and plot images

%{
% Select cell area (for GG1 eight weeks) and calculate equivalent
% resistance assuming only parallel resistances (in reality this is not the
case so the calculated resistance would not be correct, there is also sheet
resistance)

Rinv=0; % Rinv contains the sum of the inverse of all resistances
pstart=109; 
pend=554;
qstart=29;
qend=496;
Rs_cellarea=zeros(qend-qsart,pend-pstart);
for p=pstart:pend
    for q=qstart:qend
        if(~isnan(Rs_final(q,p)) && Rs_final(q,p)~=0)
            Rinv=Rinv+1/Rs_final(q,p);
            Rs_cellarea(q-28,p-108)=Rs_final(q,p);
        else
            fprintf('NaN or 0 found for indices line %d col %d\n',p,q);
        end
    end
end

Req=1/Rinv;
%}

% Calculate the average series resistance
%{
Rsum=0; % Rinv contains the sum of the inverse of all resistances
pstart=109; 
pend=554;
qstart=29;
qend=496;
% ATTENTION: p and q are reversed here. size(Rs,2)=512 and size(Rs,1)=640.
% Correct that.
Rs_cellarea=zeros(qend-qstart,pend-pstart);
for p=pstart:pend
    for q=qstart:qend
        if(~isnan(Rs_final(q,p)) && Rs_final(q,p)~=0)
            Rsum=Rsum+Rs_final(q,p);
            Rs_cellarea(q-28,p-108)=Rs_final(q,p);
        else
            fprintf('NaN or 0 found for indices line %d col %d\n',p,q);
        end
    end
end

Req=Rsum/((qend-qstart+1)*(pend-pstart+1));

% Plot Rs in the cell area only
figure
imagesc(Rs_cellarea);
hRs=colorbar;
caxis([0 10]);
ylabel(hRs, 'Rs (Ohm-cm^2)')
title('Cell area only');

display(Req); % Ohm-cm²;
%}


% plot Rs and other parameters
figure
imagesc(Rs_final);
hRs=colorbar;
caxis([0 10]);
ylabel(hRs, 'Rs (Ohm-cm^2)')
set(gca,'FontSize',18)

% Plot Vmpp
Vmpp1sun_real=Vmpp1sun;
Vmpp1sun_real(imag(Vmpp1sun_real)~=0)=NaN;

figure;
imagesc(Vmpp1sun_real); % V
% set(gca,'ColorScale','log');
caxis([0.5 0.8])
hVmpp=colorbar;
ylabel(hVmpp, '1 sun Vmpp (V)')

% C
C_real=C;
C_real(imag(C)~=0)=NaN;

figure;
imagesc(C_real); % A/cm²
set(gca,'ColorScale','log');
% caxis([1e-10 1e-6])
caxis([1e-9, 7e-9])
hC=colorbar;
ylabel(hC, 'C')
%{
% J01
J01_real=J01;
J01_real(imag(J01_real)~=0)=NaN;

figure;
imagesc(-J01_real*1e8); % pA/cm²
set(gca,'ColorScale','log');
caxis([1e-2 10])
hJ1=colorbar;
ylabel(hJ1, 'J01 (pA/cm^2)')

% J02
J02_real=J02;
J02_real(imag(J02_real)~=0)=NaN;

figure;
imagesc(-J02_real*1e-4); % A/cm²
set(gca,'ColorScale','log');
caxis([1e-9 1e-6])
hJ2=colorbar;
ylabel(hJ2, 'J02 (A/cm^2)')

% Jmpp
Jmpp1sun_real=Jmpp1sun;
Jmpp1sun_real(imag(Jmpp1sun_real)~=0)=NaN;

figure;
imagesc(Jmpp1sun_real); % A/m^2
set(gca,'ColorScale','log');
caxis([1e-2 10])
hJmpp=colorbar;
ylabel(hJmpp, 'J (A/m^2)')
%}

%% Part to check how many complex numbers are in Rs (to make sure all of them are not)
% Check the number of complex numbers in Rs
Rs_complex=imag(Rs)~=0; % Logical array of complex values in Rs
Rs_complex_logical=find(Rs_complex); % Array containing linear indices of complexes
% disp(Rs_complex_logical); % Contains the linear indices of complex numbers

% Find indices of complex numbers in the array in (x,y) form
% %{ 
Rs_complex=imag(Rs)~=0; % Logical array of complex values in Rs
Rs_complex_logical=find(Rs_complex); % Array containing linear indices of complexes
% values found in Rs
% create array containing the indices of the complex numbers
L=length(Rs_complex_logical); % number of complex numbers
compl_ind=zeros(L,2);
% Parse all linear indices and convert them into xy indices
clear i
for i=1:L
compl_ind(i,2)=floor(Rs_complex_logical(i)/512)+1; % column number corresponding to index i
compl_ind(i,1)=(Rs_complex_logical(i)/512-compl_ind(i,2)+1)*512; % row number corresponding to index i
end
% %}
