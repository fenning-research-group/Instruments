% Convert two theta values between incident x-ray energies. If no E_0
% (reference energy) is given, we assume the reference two theta values
% were generated using Cu-Kalpha radiation (typical benchtop XRD)

function twotheta_1 = twothadjust(twotheta_0, E_1, E_0)
    h = 4.135667662e-15;  %eV/s
    c = 299792458; %m/s
    
    lambda_1 = (h*c/E_1)*1e10;  % x-ray wavelength for measurement, angstroms
       
    if nargin < 3
        lambda_0 = 1.5406;           % x-ray wavelength for supplied twotheta values, in angstroms. typically Cu-Kalpha, which is 1.504 A
    else
        lambda_0 = (h*c/E_0)*1e10;  % x-ray wavelength for reference, angstroms
    end
       
    twotheta_1 = 2* asind( (lambda_1/lambda_0) * sind(twotheta_0/2) );    
end