%% taucplot.m
%
% taucplot converts a reflectance, transmittance, or absorbance spectrum into a tauc plot, then attempts to 
% determine the bandgap by plotting a best fit line to the linear region of the tauc plot. This is done by
% linearly fitting 5% of the curve in a moving window, and picking the fit with the largest R^2 value. Regions
% centered around datapoints with a tauc value < 10% of the peak value are ignored, as a large trailing flat
% region near taucvalue = 0 is expected and will throw false positives as a high R2 fit
%
% Usage:
%
% taucplot.m takes 4 input parameters:
%       wavelengths:        vector of wavelength values
%       signal:             vector of intensity values
%       signaltype:         string {'reflectance', transmittance', 'absorbance'} describing type of intensity values provided
%                           if 'reflectance', assumes data is from powder reflectance and applied a Kubleka-Munk transformation to obtain absorbance
%       bandgaptype:        string {'direct', 'indirect'} describing expected bandgap type of the material. Changes "n" factor in tauc plot
%
% Example:
%
%       mybandgap = taucplot(data.wavelengths, data.signal, 'reflectance', 'direct')
%
%       should output Eg in eV, as well as generate two plots - tauc plot and the raw reflectance plot


function Eg = taucplot(wavelengths, signal, signaltype, bandgaptype)
    
    fitwidth = round(length(signal)/20);
    fit_threshold = 0.1;

    if max(signal) > 1
        signal = signal/100;    %change 0-100 to 0-1
    end

    if strcmp(signaltype, 'reflectance')
        absorbance = ((1-signal).^2)./(2*signal);       %Kubelka-Munk transform to convert diffuse reflectance into absorbance
        ystring = 'Reflectance';
    elseif strcmp(signaltype, 'transmittance')
        absorbance = -log(signal);              %beer-lamberts to convert transmittance into absorbance
        ystring = 'Transmittance';
    elseif strcmp(signaltype, 'absorbance')
        ystring = 'Absorbance (AU)';
    else
        error('Incorrect signal type provided. Please use ''reflectance'', ''transmittance'', or ''absorbance''');;
    end
    
    if strcmp(bandgaptype, 'direct')
        n = 0.5;        %direct bandgap constant
    elseif strcmp(bandgaptype, 'indirect')
        n = 2;          %indirect bandgap constant
    else
        error('Incorrect bandgap type provided. Please use ''direct'' or ''indirect''');
    end
    
    c = 3e8;                    %speed of light, m/s
    h = 4.13567E-15;            %planck's constant, eV
    nu = c./(wavelengths*1e-9);  %convert nm to hz
    ev = 1240./wavelengths;     %convert nm to ev
          
    taucvalue = (absorbance.*h.*nu) .^ (1/n);
    
    bestfit = [];
    bestfit_rsquare = 0;   

    for idx = (fitwidth/2)+1 : length(ev) - fitwidth/2
        if taucvalue(idx) >= max(taucvalue)*fit_threshold
            [testfit, testgof] = fit(ev(idx - fitwidth/2:idx + fitwidth/2), taucvalue(idx - fitwidth/2:idx + fitwidth/2), 'poly1');
            if testgof.rsquare > bestfit_rsquare && testfit.p1 > 0
                bestfit = testfit;
                bestfit_rsquare = testgof.rsquare;
            end
        end
    end
    
    
    figure, hold on
    plot(wavelengths, signal, 'b');
    xlabel('Wavelength (nm)')
    ylabel(ystring);
    title('Raw Data for Tauc Plot');
    
    figure, hold on;
    plot(ev, taucvalue, 'b');
    
    ylim_max = max(ylim);
    plot(bestfit, 'r:'); 
    ylim([0, ylim_max]);
    title('Tauc Plot, Direct Bandgap');
    xlabel('Photon Energy (eV)');
    if n == 0.5
        ylabel('({\alpha}h{\nu})^2');   
    else
        ylabel('({\alpha}h{\nu})^1^/^2');
    end
    set(findobj(gcf, 'type', 'legend'), 'visible', 'off');  %remove legend
    
    Eg = -bestfit.p2/bestfit.p1;
    
    text(min(xlim) + range(xlim)*0.1, 0.9*max(ylim), sprintf('Eg: %.2f', Eg));
    
end