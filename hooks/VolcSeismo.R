#Load libraries and data
knitr::opts_chunk$set(echo = TRUE)
suppressMessages(library(dplyr))
suppressMessages(library(chron))
suppressMessages(library(e1071))
suppressMessages(library(tseries))
suppressMessages(library(fpp2))
suppressMessages(library(zoo))
suppressMessages(library(caret))
suppressMessages(library(randomForest))
suppressMessages(library(RSEIS))
suppressMessages(library(gatepoints))

runAnalysis <- function(data){
    time=as.POSIXct(data[,1],format = "%Y-%m-%dT%H:%M:%S")
    dataZ=data[,2]
    dataN=data[,3]
    dataE=data[,4]
    #plot(time,dataZ,las=1,type='l')

    window=500   #the features are calculated in time windows of 'window'/50 seconds
    LP=c();freq_max1=c();freq_max10=c();freq_max20=c();freq_max30=c();freq_max40=c();freq_max50=c();
    freq_max60=c();freq_max70=c();freq_max80=c();freq_max90=c();freq_max100=c();time_parameters=c();
    ssa_max1=c();ssa_max10=c();ssa_max20=c();ssa_max30=c();ssa_max40=c();ssa_max50=c();ssa_max60=c();
    ssa_max70=c();ssa_max80=c();ssa_max90=c();ssa_max100=c();rsam=c();sd_freq_max10=c();sd_freq_max20=c();
    sd_freq_max30=c();sd_freq_max40=c();sd_freq_max50=c();sd_freq_max60=c();sd_freq_max70=c();
    sd_freq_max80=c();sd_freq_max90=c();sd_freq_max100=c();
    sd_ssa_max10=c();sd_ssa_max20=c();sd_ssa_max30=c();sd_ssa_max40=c();sd_ssa_max50=c();sd_ssa_max60=c();
    sd_ssa_max70=c();sd_ssa_max80=c();sd_ssa_max90=c();sd_ssa_max100=c();sd_rsam=c()
    time_parameters=c()


    steps=50  #50 to have 1s sliding window 
    for (j in seq(window,length(dataZ),steps)){
    #for (j in window){
    aux_signal=dataZ[(j-window+1):j]    #backward 1s-sliding windows of 10 s
    #aux_time=time[(j-window+1):j]
    #plot(aux_time,aux_signal,type='l')
    spectrum=Spectrum(aux_signal, 1/50, one_sided = TRUE, type = 3, method = 1)
    spectrum=cbind(spectrum$f,spectrum$spectrum)
    #plot_spectrum(data=spectrum, unit="linear")
    spectrum[,1]=spectrum[,1][order(spectrum[,2],decreasing = TRUE)]    #order the amplitudes in decreasing order
    spectrum[,2]=spectrum[,2][order(spectrum[,2],decreasing = TRUE)]    #order the amplitudes in decreasing order
    
    freq_max1=append(freq_max1,spectrum[1,1])
    freq_max10=append(freq_max10,median(spectrum[1:10,1]))
    freq_max20=append(freq_max20,median(spectrum[1:20,1]))
    freq_max30=append(freq_max30,median(spectrum[1:30,1]))
    freq_max40=append(freq_max40,median(spectrum[1:40,1]))
    freq_max50=append(freq_max50,median(spectrum[1:50,1]))

    sd_freq_max10=append(sd_freq_max10,sd(spectrum[1:10,1]))
    sd_freq_max20=append(sd_freq_max20,sd(spectrum[1:20,1]))
    sd_freq_max30=append(sd_freq_max30,sd(spectrum[1:30,1]))
    sd_freq_max40=append(sd_freq_max40,sd(spectrum[1:40,1]))
    sd_freq_max50=append(sd_freq_max50,sd(spectrum[1:50,1]))
        
    ssa_max1=append(ssa_max1,spectrum[1,2])
    ssa_max10=append(ssa_max10,median(spectrum[1:10,2]))
    ssa_max20=append(ssa_max20,median(spectrum[1:20,2]))
    ssa_max30=append(ssa_max30,median(spectrum[1:30,2]))
    ssa_max40=append(ssa_max40,median(spectrum[1:40,2]))
    ssa_max50=append(ssa_max50,median(spectrum[1:50,2]))
        
    sd_ssa_max10=append(sd_ssa_max10,sd(spectrum[1:10,2]))
    sd_ssa_max20=append(sd_ssa_max20,sd(spectrum[1:20,2]))
    sd_ssa_max30=append(sd_ssa_max30,sd(spectrum[1:30,2]))
    sd_ssa_max40=append(sd_ssa_max40,sd(spectrum[1:40,2]))
    sd_ssa_max50=append(sd_ssa_max50,sd(spectrum[1:50,2]))
        
    rsam=append(rsam,median(abs(aux_signal)))
    sd_rsam=append(sd_rsam,sd(abs(aux_signal)))
        
    time_parameters=append(time_parameters,substr(time[j],1,23))
    }
        
    matrix_of_features=as.data.frame(cbind(as.character(time_parameters),freq_max1,freq_max10,freq_max20,freq_max30,freq_max40,freq_max50,sd_freq_max10,sd_freq_max20,sd_freq_max30,sd_freq_max40,sd_freq_max50,ssa_max1,ssa_max10,ssa_max20,ssa_max30,ssa_max40,ssa_max50,sd_ssa_max10,sd_ssa_max20,sd_ssa_max30,sd_ssa_max40,sd_ssa_max50,rsam,sd_rsam))
    return(matrix_of_features)
}