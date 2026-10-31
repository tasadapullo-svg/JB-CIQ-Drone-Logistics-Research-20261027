QGIS 3.22.4 LABEL FIX V2
1. Unzip the whole archive, preserving code/ and data/ folders.
2. Save the QGIS project currently open (the build clears it).
3. Open QGIS Python console, paste the one-line command from code/RUN_ONE_LINE_IN_QGIS_CONSOLE.txt.
4. In the file picker select code/01_BUILD_COMPLETE_QGIS322.py inside the unzipped directory.
5. Wait for all layout exports; open CIQ_ABC_FINAL_REVIEW.qgz.
V2 fixes three invalid QGIS label expressions in V1.
All 69 labels use concat(ID, ' | ', name); original node data is unchanged.
The source is statically checked; QGIS runtime rendering must be checked on your computer.
