{pkgs}: {
  deps = [
    pkgs.openjpeg
    pkgs.libwebp
    pkgs.lcms2
    pkgs.freetype
    pkgs.libtiff
    pkgs.libpng
    pkgs.libjpeg
    pkgs.xorg.libX11
    pkgs.xorg.libXdmcp
    pkgs.xorg.libXau
    pkgs.python312Full
    pkgs.stdenv.cc.cc.lib
    pkgs.zlib
  ];
  env = {
    PYTHONBIN = "${pkgs.python312Full}/bin/python3.12";
    LANG = "en_US.UTF-8";
    STDERROUT = "1";
    LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
      pkgs.stdenv.cc.cc.lib
      pkgs.zlib
    ];
  };
}