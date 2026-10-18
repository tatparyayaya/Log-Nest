$desktop = [Environment]::GetFolderPath('Desktop')
$wsh = New-Object -ComObject WScript.Shell
$shortcut = $wsh.CreateShortcut("$desktop\LOG NEST.lnk")
$shortcut.TargetPath = "d:\LOG_NEST\dist\LogNest\LogNest.exe"
$shortcut.WorkingDirectory = "d:\LOG_NEST\dist\LogNest"
$shortcut.IconLocation = "d:\LOG_NEST\dist\LogNest\LogNest.exe,0"
$shortcut.Description = "LOG NEST - Windows Activity Tracker"
$shortcut.Save()

# Also create shortcut in the project root
$rootShortcut = $wsh.CreateShortcut("d:\LOG_NEST\LOG NEST.lnk")
$rootShortcut.TargetPath = "d:\LOG_NEST\dist\LogNest\LogNest.exe"
$rootShortcut.WorkingDirectory = "d:\LOG_NEST\dist\LogNest"
$rootShortcut.IconLocation = "d:\LOG_NEST\dist\LogNest\LogNest.exe,0"
$rootShortcut.Description = "LOG NEST - Windows Activity Tracker"
$rootShortcut.Save()

Write-Output "Shortcuts created successfully on Desktop and Project Root."
