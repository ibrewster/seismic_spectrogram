# What are hooks?

Simply put, hooks are anything the user wants them to be. The end user can place any valid python file in this directory, and it will be run when generating the spectrograms.

# How do I make hooks?

The only requirement for a hook is that it contains a function named `run` that takes a single argument. This argument will be the raw seismic waveform data retrieved and filtered by the spectrogram generation function. The hook can then do whatever it wishes with the data. No return value is expected or used.