function plotPLMap(PLdat, plot_peak_wavelength)
    
    numpts_x = size(PLdat.data, 2);
    numpts_y = size(PLdat.data, 1);
    
    min_x = PLdat.data(1,1).x;
    min_y = PLdat.data(1,1).y;
    
    max_x = PLdat.data(end,end).x;
    max_y = PLdat.data(end,end).y;
        
    x_grid = zeros(numpts_y, numpts_x);
    y_grid = x_grid;
    pl_peak = x_grid;
    pl_int = x_grid;
    
    idx = 1;
    
    for m = 1:size(x_grid, 1)
        for n = 1:size(x_grid, 2)
            x_grid(m,n) = PLdat.data(m,n).x;
            y_grid(m,n) = PLdat.data(m,n).y;
            pl_int(m,n) = log(PLdat.data(m,n).peak.counts);
%             tempfit = fit(PLdat.data(m,n).shift, PLdat.data(m,n).counts, 'gauss1');
%             pl_peak(m,n) = tempfit.b1;
            pl_peak(m,n) = PLdat.data(m,n).peak.wavelength;
        end
    end
    
    x_grid = x_grid - min(x_grid(:));   %to take care of negative relative positions if x/y series put in reverse somehow
    y_grid = y_grid - min(y_grid(:));
    x_grid = fliplr(x_grid);
    y_grid = flipud(y_grid);        % XY stage maps from top-right to bottom-left of sample, with top-right as (0,0). flip both axes so bottom-left is (0,0)
    
    hfig = figure;
    
    %plot exact measured points imagesc (from loadmda.m)
    if plot_peak_wavelength == 1
        imagesc(x_grid(1,:),y_grid(:,1),pl_peak);
        hcb = colorbar;
        hcb.Title.String = {'Peak Wavelength'}; 
        title(['PL Wavelength Map']);
    else
        imagesc(x_grid(1,:),y_grid(:,1),pl_int); 
        hcb = colorbar;
        hcb.Title.String = {'Peak Counts (log)'}; 
        title(['PL Intensity Map']);
    end
    

    cmap = cbrewer('seq', 'YlGnBu', 256);
    colormap(cmap);    
    xlabel('X Position (\mum)');
    ylabel('Y Position (\mum)');
    xlim([0 max(x_grid(:))]);
    ylim([0 max(y_grid(:))]);
    pbaspect([1 1 1]);
    prettyplot;
    
    %% Interactive tooltip to display scan on plot
    
    %data to be passed to click function that generates plots
    clickdata.PLdat = PLdat.data;
    clickdata.incidentwavelength = PLdat.incidentwavelength;
    clickdata.x_grid = x_grid;
    clickdata.y_grid = y_grid;
    
    set(hfig, 'UserData', clickdata);
    
    hclick = datacursormode(hfig);
    set(hclick, 'DisplayStyle', 'Window',...
                'Enable', 'on',...
                'UpdateFcn', @click4spectrum);
end

function txt = click4spectrum(~, event_obj)
    position_tolerance = 0.0001;        % used to avoid rounding errors from preventing scan index lookup by comparing click position to data
    
    position = get(event_obj, 'Position');
    hfig =get(event_obj, 'Target');
    data = hfig.Parent.Parent.UserData;
    
    xidx = find(abs(data.x_grid(1,:) - position(1)) < position_tolerance);
    yidx = find(abs(data.y_grid(:,1) - position(2)) < position_tolerance);
    pl_int = data.PLdat(yidx, xidx).peak.counts;
    pl_pos = data.PLdat(yidx, xidx).peak.wavelength;
    
    figure(201);
    wl = data.PLdat(yidx, xidx).wavelength;
    spec = data.PLdat(yidx, xidx).counts;
    incident_wl = data.incidentwavelength;
%     absspec = -log(0.01*spec);
%     wl = shift_to_wl(shift, incident_wl);
    
%     fitobj = fit(wl, spec, 'gauss1');
    
    plot(wl, spec, 'o', 'color', [0.2157, 0.4941, 0.7216, 0.1], 'markersize', 2);
%     hold on;
%     plot(fitobj, 'r');
%     hold off;
    title(['X: ' num2str(position(1)) ' Y: ' num2str(position(2))]);
%     xlabel('Raman Shift (cm^{-1})');
    xlabel('Wavelength (nm)');
    ylabel('Counts');
    
    txt = {['X:       ' num2str(position(1)) ' um'],...
           ['Y:       ' num2str(position(2)) ' um'],...
           ['PL peak: ' num2str(pl_pos) ' nm'],...
           ['PL intensity: ' num2str(pl_int), ' counts'],...
           };
    figure(hfig.Parent.Parent);
end


%converts a raman shift (cm-1) to the emission wavelength (nm) given the
%incident wavelength (nm). positive shift = stokes shift (to lower
%wavenumber)
function emitted = shift_to_wl(shift, incident)
    incident_wavenumber = 1./(incident * 1e-7);
    emitted_wavenumber = incident_wavenumber - shift;
    emitted = 1e7./(emitted_wavenumber);
end