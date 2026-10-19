# Create a 3D city model for the big assignment

Follow these instructions to combine 3DBAG tiles, remove selected buildings, and create a CityGML model for Cesium ion.

Run all commands from the project folder containing `merge.py`.

## Dependencies

Create a Python virtual environment and install `cjio`:

>If you use **PyCharm**, select your project's virtual environment as the Python interpreter. Open **View > Tool Windows > Python Packages**, search for `cjio`, and click **Install**. See the [PyCharm package installation guide](https://www.jetbrains.com/help/pycharm/installing-uninstalling-and-upgrading-packages.html) for details.

**Windows — Command Prompt (`cmd.exe`)**

```cmd
python -m venv venv
.\venv\Scripts\activate.bat
python -m pip install cjio
```

**Linux/macOS — Bash or Zsh**

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install cjio
```


The conversion tool requires **Java 17 or newer**. You can download a Java SE Development Kit (JDK) from [Oracle](https://www.oracle.com/java/technologies/downloads/). Ensure that Java is available on your `PATH`. After installation of Java SE, close and reopen your terminal or IDE, then check the installed version:

```text
java -version
```

If it is not found try restarting your computer. If the issue still not resilved try adding JAVA to `PATH` manually or ask the assistance of course staff.


The software `citygml-tools` should already be included next to this file, but if not, dowload [citygml-tools 2.5.0](https://github.com/citygml4j/citygml-tools/releases/tag/v2.5.0). Extract the complete package into the project folder so that the launcher is located at:

- Windows: `citygml-tools-2.5.0/citygml-tools.bat`
- Linux/macOS: `citygml-tools-2.5.0/citygml-tools`

On Linux/macOS, you might need to make the launcher executable:

```bash
chmod +x ./citygml-tools-2.5.0/citygml-tools
```

## Preparing the 3D buildings for Cesium ION.


1. Go to the [3DBAG downloads page](https://3dbag.nl/en/download). Select the tiles covering your area of interest and download them in **CityJSON** format. Place the `*.city.json` files directly in the project's `data` subfolder. Create this folder if necessary and extract any compressed downloads first.

2. Open the [3DBAG viewer](https://3dbag.nl/en/viewer?basemap=standaard&lod=lod22&rdx=89717.07966557384&rdy=436983.5903027065&ox=-5.820766091346741e-11&oy=9713.390711649296&oz=1240.989919038061). Click a building you want to remove, open the **Attributes** panel, and find `identificatie`. Copy the complete value, including the `NL.IMBAG.Pand.` prefix, into `to_remove.txt` in the project folder. Put each identifier on a separate line, without quotation marks. Repeat for every building you want to remove.

3. With the virtual environment active, run:

   ```text
   python merge.py
   ```

   The script merges the tiles, removes the buildings listed in `to_remove.txt`, and creates `merged.city.json`. It then converts this file to `merged.city.gml` for Cesium ion. Both output files are saved in the project folder, outside `data`.

4. Open `merged.city.gml` in the [CityGML Viewer](https://transfer.hft-stuttgart.de/pages/citydoctor/citygml-viewer/). Check that the buildings you intended to remove are absent and that the buildings you want to keep are still present.

5. Upload `merged.city.gml` to **Cesium ion** and select the **CityGML** import option. Wait for tiling to finish, then inspect the model in the asset preview. Tiling may take some time, depending on the size of the model. You may rename the file.
