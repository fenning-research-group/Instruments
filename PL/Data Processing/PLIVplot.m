function PLIVplot(datastruc, nb_V, nb_int, figure_nb,image_nb)
% Function to plot PLIV images
% data struc:       Structure array containing the PLIV data
% nb_V:             Number of voltage values used in PLIV measurements
%                   (excludes two first Jsc maps)
% nb_int:           Number of intensity values used in PLIV measurements
%                   (excludes two first Jsc maps)
% figure_nb:        Figure number
%                       1: net background-corrected images (obtained by substracting Jsc image)
%                       2: background-corrected images (before Jsc image
%                       subtraction)
% image_nb:         Number of the image to plot (1 for 0 V and 0 sun, 2 for
%                   0 V and 1 sun, 3,4,... for other PLIV images)

if(figure_nb==1)
    figure(1) % net background-corrected images plotted in fig 1
    subplot(nb_int+1,nb_V,image_nb); 
    imagesc(datastruc(1).netimage); % Plot net images
    c=colorbar;
    c.FontSize=11;
    I=datastruc(image_nb).current;
    V=datastruc(image_nb).set_voltage;
    int=datastruc(image_nb).intensity;
    title_str=sprintf('%2.0f mV, %.1f sun, %2.0f mA',V*1e3,int,I*1e3);
    title(title_str,'FontSize',11);
elseif(figure_nb==2) % background-corrected images without Jsc correction
    figure(2)
    subplot(nb_int+1,nb_V,image_nb);
    imagesc(datastruc(image_nb).image_bgc); % Plot net images
    c=colorbar;
    c.FontSize=11;
    I=datastruc(image_nb).current;
    V=datastruc(image_nb).set_voltage;
    int=datastruc(image_nb).intensity;
    title_str=sprintf('%2.0f mV, %.1f sun, %2.0f mA',V*1e3,int,I*1e3);
    title(title_str,'FontSize',11);
end
