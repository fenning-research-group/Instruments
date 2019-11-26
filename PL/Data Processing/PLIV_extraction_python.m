% PLIV_extraction_python
% 10/9/2019
% Extraction of solar cell parameters from PLIV images at different
% voltages AND different laser intensities from an h5py file.

% add to path folders containing general processing functions
%addpath('G:\My Drive\Scripts\Utilities');
%addpath('G:\My Drive\Scripts\Utilities\export_fig');
%addpath('G:\My Drive\PVRD2 WaRM\Experiments\'FLIR PL-EL Setup\Matlab');
%addpath('G:\My Drive\Scripts\Colormaps');

% Constants
k=1.38e-23; % J/K
qC=1.6022e-19; % C
T=298.14; % K
VT=k*T/qC;
cellarea=((2*2.54)^2)*1e-4; % Cell area (m²) (actually the cell width is 47 mm).

% folder='G:\Shared drives\FenningLab2\groupMembers\Guillaume\PLIVtest_newsetup';
% folder='C:\Users\Guillaume\Documents\#UCSD\2_PVRD2_water_degradation\Results\PLIV_tests\test_fulldata';
folder='G:\My Drive\PVRD2 WaRM\Experiments\Damp Heat Cell Degradation Testing\Round 2\Data\PL, EL, PLIV\20191120';
% file='frgPL_20191009_0002_Test_GG_Al_10_PLIV.h5';
% file='frgPL_20191031_0002_GB8.h5';
% file='frgPL_20191030_0002_GB11.h5';
% file='frgPL_20191023_0002_GB11.h5'; % The file 'frgPL_20191031_0006_GB5.h5' has exploitable data (laser was on)
file='frgPL_20191120_0001_GB11.h5';
filepath=fullfile(folder,file);

%% Load data
%{
meascurr=h5read(filepath,'/data/i'); % Measured current
measvolt=h5read(filepath,'/data/v'); % Measured voltage
maps=h5read(filepath,'/data/image_bgc'); % PL maps after background correction
intensity=h5read(filepath,'/settings/suns'); % Intensity data obtained from the calibration based on measure Jsc
set_voltage=h5read(filepath,'/settings/vbias') ; % Voltage set for each measurement
%}

%% Load data
% %{
notes = h5read(filepath, '/settings/notes');
idx = contains(notes, 'PLIV');  %filter measurements taken for PLIV

meascurr=h5read(filepath,'/data/i'); % Measured current
meascurr = meascurr(idx);

measvolt=h5read(filepath,'/data/v'); % Measured voltage
measvolt = measvolt(idx);

maps=h5read(filepath,'/data/image_bgc'); % PL maps after background correction
maps = maps(:,:,idx);

intensity=h5read(filepath,'/settings/suns'); % Intensity data obtained from the calibration based on measure Jsc
intensity = intensity(idx);

set_voltage=h5read(filepath,'/settings/vbias') ; % Voltage set for each measurement
set_voltage = set_voltage(idx);

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
Rs_raw=zeros(size(lumstruc(1).image_bgc));
J01_raw=zeros(size(lumstruc(1).image_bgc));
J02_raw=zeros(size(lumstruc(1).image_bgc));
Voc1sun_raw=zeros(size(lumstruc(1).image_bgc));
Jmpp1sun_raw=zeros(size(lumstruc(1).image_bgc));
Vmpp1sun_raw=zeros(size(lumstruc(1).image_bgc));
FF1sun_raw=zeros(size(lumstruc(1).image_bgc));
nu1sun_raw=zeros(size(lumstruc(1).image_bgc));
C_raw=zeros(size(lumstruc(1).image_bgc));
% The images are found as lumstruc.PLIV(i).image.mean;

% Calculate resistance
% GB2=PLIVmatrix(GB2);
[M,N,lumstruc]=PLIVmatrix_python(lumstruc,cellarea); % Need to add arguments here to select which images to use

%% Indices of interesting IV curve points

% Find index at 1 sun and Vmpp conditions.
mpp1sun_ind=0;
for ii=1:L
    if(lumstruc(ii).intensity==1 && lumstruc(ii).set_voltage==lumstruc(3).set_voltage) % The first Vmpp value is in line 3 (but usually not at 1 sun)
        mpp1sun_ind=ii; % Point at 1 sun and at max power point voltage
    end    
end
% Display warning if the 1 sun max power point was not found
if(mpp1sun_ind==0)
    warn_str=['No 1 sun max power point conditions found, using instead'...
        'conditions at 1 sun and Voc'];
    warning(warn_str);
    mpp1sun_ind=1; % Corresponds to data at 1 sun and Voc
end

% Find index at 1 sun and short-circuit conditions
clear ii;
sc1sun_ind=0;
for ii=1:L
    if(lumstruc(ii).intensity==1 && lumstruc(ii).set_voltage==0)
        sc1sun_ind=ii; % Point at 1 sun and at max power point voltage
    end    
end
% Display warning if the 1 sun max power point was not found
if(sc1sun_ind==0)
    warn_str=['No 1 sun short-circuit conditions found, using instead'...
        'the second index (check that it is at short-circuit).'];
    warning(warn_str);
    sc1sun_ind=2; % Should correspond to short-circuit conditions, the intensity will depends on data acquisition settings.
end

voc1sun_ind=1; % Voc measurement at 1 sun is in the first row of lumstruc
Pin1sun=1e3; % Incidnet 1-sun power (W/m2)

%% Correct Voc image at 1 sun
% Voc image at 1 sun
lumstruc(1).netimage=lumstruc(i).image_bgc-lumstruc(sc1sun_ind).image_bgc; % corrected with Jsc image at 1 sun

%% Extract mapped solar cell parameters
for p=1:size(M,1) % For all pixel columns
    for q=1:size(M,2) % For all pixel lines
        % X{p,q}=M{p,q}\N{p,q};
        X{p,q}=linsolve(M{p,q},N{p,q});
        Rs_raw(p,q)=X{p,q}(2); % The Rs value is in the second element of vector X
        C_raw(p,q)=exp(X{p,q}(1)/VT);
        J01_raw(p,q)=-X{p,q}(3)*C(p,q)/Rs(p,q);
        J02_raw(p,q)=-X{p,q}(4)*sqrt(C(p,q))/Rs(p,q);
        Voc1sun_raw(p,q)= VT*log(lumstruc(voc1sun_ind).netimage(p,q)/C(p,q)); 
        Vmpp1sun_raw(p,q)=VT*log(lumstruc(mpp1sun_ind).netimage(p,q)/C(p,q)); % V %
        Jmpp1sun_raw(p,q)=-J01(p,q)*(exp(Vmpp1sun(p,q)/VT)-1)-J02(p,q)*(exp(Vmpp1sun(p,q)/(2*VT))-1)+lumstruc(sc1sun_ind).current/cellarea; % A/m²
        FF1sun_raw(p,q)=lumstruc(mpp1sun_ind).voltage*Jmpp1sun(p,q)*cellarea/(lumstruc(sc1sun_ind).current*Voc1sun(p,q))*100; % FF=Vmpp*Jmpp,xy/(Jsc*Voc,xy) where Jmpp,xy and Voc,xy are maps and Vmpp and Jsc are scalars.
%         nu1sun(p,q)=FF1sun(p,q)*lumstruc(sc1sun_ind).current*lumstruc(voc1sun_ind).voltage/(Pin1sun*cellarea); % 1 sun efficiency map
        nu1sun_raw(p,q)=FF1sun(p,q)*lumstruc(sc1sun_ind).current*Voc1sun(200,200)/(Pin1sun*cellarea); % 1 sun efficiency map. Use a Voc point from the map as the Voc data in lumstruc is wrong for some reason
    end
end

% Plot output parameters in a subplot
fig4by4=figure('Position',[30 800 1200 900]);
subplot(2,2,1);
% Plot Voc map at 1 sun
[figVoc,hVoc,Voc1sun]=plotmap(Voc1sun_raw);
ylabel(hVoc,'1 sun Voc (V)');
caxis([0.5,0.8]);

subplot(2,2,2);
% Plot fill factor map at 1 sun
[figFF,hFF,FF1sun]=plotmap(FF1sun_raw);
ylabel(hFF,'1 sun FF (%)');
caxis([20, 100]);

subplot(2,2,3);
% Plot efficiency map at 1 sun
[figNu,hNu,nu1sun]=plotmap(nu1sun_raw);
ylabel(hNu,'Efficiency at 1 sun (%)');
caxis([0, 30]);

subplot(2,2,4);
% Plot series resistance
Rs_cm2_raw=-Rs_raw*1e4; % Final series resistance in Ohm-cm²
[figRs,hRs,Rs_cm2]=plotmap(Rs_cm2_raw);
caxis([0 10]);
ylabel(hRs, 'Rs (Ohm-cm^2)');
caxis([0, 10]);

savefig(fig4by4,fullfile(folder,file(1:end-3)+"_outputfig"));

% Plot Vmpp
Vmpp1sun=Vmpp1sun_raw;
Vmpp1sun(imag(Vmpp1sun)~=0)=NaN;
Vmppfig=figure;
imagesc(Vmpp1sun); % V
% set(gca,'ColorScale','log');
caxis([0.5 0.8])
hVmpp=colorbar;
ylabel(hVmpp, '1 sun Vmpp (V)')
set(gca,'FontSize',16);
savefig(Vmppfig,fullfile(folder,file(1:end-3)+"_1sunVmpp"));

% C
C=C_raw;
C(imag(C)~=0)=NaN;

Cfig=figure;
imagesc(C); % A/cm²
% set(gca,'ColorScale','log');
% caxis([1e-10 1e-6])
% caxis([1e-9, 7e-9])
set(gca,'ColorScale','log');
caxis([1e-8 1e-7])
hC=colorbar;
ylabel(hC, 'C');
set(gca,'FontSize',16);
savefig(Cfig,fullfile(folder,file(1:end-3)+"_Plconst"));

% Process and plot images

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

% save data in h5 file
%(correct this as only the J02map is currently saved using the following code)
h5name=fullfile(folder,file(1:end-3)+"_fitted.h5");
hdf5write(h5name,'/CMap',C);
hdf5write(h5name,'/RsMap',Rs_cm2);
hdf5write(h5name,'/FF1sunMap',FF1sun);
hdf5write(h5name,'/Vmpp1sunMap',Vmpp1sun);
hdf5write(h5name,'/Voc1sunMap',Voc1sun);
hdf5write(h5name,'/nu1sunMap',nu1sun);
hdf5write(h5name,'/J01Map',J01);
hdf5write(h5name,'/J02Map',J02);

% Save data in .mat file
Matname=fullfile(folder,file(1:end-3)+"_fitted.mat");
save(Matname,'lumstruc','C','Rs_cm2','FF1sun','Vmpp1sun','Voc1sun','nu1sun','J01','J02');

% Function to plot real part of the maps
% Returns figure and colorbar handles
function [fig,h,A_real]=plotmap(A)
fig=0;
A_real=A;
A_real(imag(A_real)~=0)=NaN;
%fig=figure;
imagesc(A_real); % V
h=colorbar;
set(gca,'FontSize',18);
end


