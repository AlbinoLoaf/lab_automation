import matplotlib.pyplot as plt

# Example readings from Marius
readings = [
    237, 344, 294, 37, 430, 999,
     89, 211, 270, 208, 430, 999,
     40, 111, 42, 124, 430, 999
]

channels = [
    ("FZ", 450), ("FY", 555), ("FXL", 600), ("NIR", 855),
    ("VIS_TL_0", None), ("VIS_BR_0", None),
    ("F2", 425), ("F3", 475), ("F4", 515), ("F6", 640),
    ("VIS_TL_1", None), ("VIS_BR_1", None),
    ("F1", 405), ("F7", 690), ("F8", 745), ("F5", 550),
    ("VIS_TL_2", None), ("VIS_BR_2", None)
]

spectral = sorted(
    [
        (wavelength, readings[i], name)
        for i, (name, wavelength) in enumerate(channels)
        if wavelength is not None
    ]
)

wavelengths = [item[0] for item in spectral]
intensities = [item[1] for item in spectral]

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))

ax1.plot(wavelengths, intensities, marker="o")
ax1.set_xlabel("Nominal channel center wavelength (nm)")
ax1.set_ylabel("Raw sensor counts")
ax1.set_title("AS7343 Spectral Channels")
ax1.grid(True, alpha=0.3)


clear_names = [
    name for name, wavelength in channels
    if wavelength is None
]
clear_values = [
    readings[i] for i, (name, wavelength) in enumerate(channels)
    if wavelength is None
]

ax2.plot(clear_names, clear_values, marker="o")
ax2.set_xlabel("Clear channel")
ax2.set_ylabel("Raw sensor counts")
ax2.set_title("Additional Clear-Channel Readings")
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()