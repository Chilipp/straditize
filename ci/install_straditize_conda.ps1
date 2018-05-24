# script to install straditize-conda under Windows


function InstallStraditize ($architecture, $python_home) {
    Write-Host "Installing straditize-conda for" $architecture "bit architecture to" $python_home
    if (Test-Path $python_home) {
        Write-Host $python_home "already exists, skipping."
        return $false
    }
    if ($architecture -match "32") {
        $platform_suffix = "x86"
    } else {
        $platform_suffix = "x86_64"
    }
    $basedir = $pwd.Path + "\"
    $filename = "straditize-conda-*-Windows-" + $platform_suffix + ".exe"
    $filepath = $basedir + $filename
    $filepath = Resolve-Path $filepath
    Write-Host "Installing" $filepath "to" $python_home
    $install_log = $python_home + ".log"
    $args = "/S /D=$python_home"
    Write-Host $filepath $args
    Start-Process -FilePath $filepath -ArgumentList $args -Wait -Passthru
    if (Test-Path $python_home) {
        Write-Host "Straditize ($architecture) installation complete"
    } else {
        Write-Host "Failed to install Python in $python_home"
        Get-Content -Path $install_log
        Exit 1
    }
}


function main () {
    InstallStraditize $env:PYTHON_ARCH $env:STRADITIZE_PYTHON
}

main
