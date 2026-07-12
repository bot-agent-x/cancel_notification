# Task Scheduler Setup Script

$TaskName = "TherapistAvailabilityMonitor"
$ScriptPath = "c:\Users\吉田剛（TsuyoshiYoshida）\OneDrive - 株式会社ストラテジーテック・コンサルティング\デスクトップ\GitHub\cancel_notification\monitor.py"
$WorkingDirectory = "c:\Users\吉田剛（TsuyoshiYoshida）\OneDrive - 株式会社ストラテジーテック・コンサルティング\デスクトップ\GitHub\cancel_notification"
$PythonPath = "python"

# Remove existing task if exists
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed existing task: $TaskName"
}

# Create action
$Action = New-ScheduledTaskAction `
    -Execute $PythonPath `
    -Argument $ScriptPath `
    -WorkingDirectory $WorkingDirectory

# Create trigger (at logon)
$Trigger = New-ScheduledTaskTrigger -AtLogon

# Create settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5)

# Register task
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Therapist Availability Monitor" `
    -User $env:USERNAME `
    -RunLevel Highest

Write-Host "Task registered: $TaskName"
Write-Host "Will run automatically at next logon"
