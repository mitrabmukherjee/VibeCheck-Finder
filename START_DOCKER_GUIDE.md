# How to Start Docker Desktop on Windows

## Step-by-Step Instructions

### 1. Find Docker Desktop

**Option A: Start Menu**
1. Click the Windows Start button (bottom-left corner)
2. Type "Docker Desktop"
3. Click on "Docker Desktop" when it appears

**Option B: Desktop Shortcut**
- If you have a Docker Desktop icon on your desktop, double-click it

**Option C: Search**
- Press `Windows Key + S` to open search
- Type "Docker Desktop"
- Click the application

### 2. Wait for Docker to Start

After launching Docker Desktop:

1. **Initial Launch**: A Docker Desktop window will open
2. **Starting Up**: You'll see "Docker Desktop is starting..."
3. **System Tray**: Look for the Docker whale icon in your system tray (bottom-right corner, near the clock)
4. **Ready**: When the whale icon stops animating and shows "Docker Desktop is running", it's ready

**This can take 1-3 minutes on first launch.**

### 3. Verify Docker is Running

**Check System Tray:**
- Look for the Docker whale icon in the system tray (bottom-right)
- Click the icon - it should say "Docker Desktop is running"

**Check in PowerShell:**
```powershell
docker --version
```

You should see output like: `Docker version 24.0.x, build xxxxx`

### 4. Accept Terms (First Time Only)

If this is your first time running Docker Desktop:
1. You may see a "Docker Subscription Service Agreement"
2. Read and accept the terms
3. Docker will continue starting

### 5. Troubleshooting

#### Issue: "Docker Desktop requires a newer WSL kernel version"

**Solution:**
1. Open PowerShell as Administrator (right-click Start → "Windows PowerShell (Admin)")
2. Run: `wsl --update`
3. Restart your computer
4. Try starting Docker Desktop again

#### Issue: "Hardware assisted virtualization and data execution protection must be enabled"

**Solution:**
1. Restart your computer
2. Enter BIOS/UEFI settings (usually press F2, F10, or Del during startup)
3. Enable "Virtualization Technology" or "VT-x" or "AMD-V"
4. Save and exit BIOS
5. Start Docker Desktop again

#### Issue: Docker Desktop won't start or crashes

**Solution:**
1. Close Docker Desktop completely
2. Open Task Manager (Ctrl+Shift+Esc)
3. End any "Docker Desktop" processes
4. Try starting Docker Desktop again
5. If still failing, restart your computer

#### Issue: "Docker Desktop is unable to start"

**Solution:**
1. Check if Hyper-V or WSL 2 is enabled:
   - Open PowerShell as Administrator
   - Run: `wsl --status`
2. If WSL is not installed:
   - Run: `wsl --install`
   - Restart your computer
3. Try starting Docker Desktop again

### 6. Once Docker is Running

When you see "Docker Desktop is running" in the system tray, come back and let me know!

I'll then:
1. Start Qdrant container
2. Run the Netflix data pipeline
3. Load all 500 Netflix items into your system

---

## Quick Reference

**Start Docker Desktop:**
- Windows Start → Type "Docker Desktop" → Click

**Check if Running:**
- Look for whale icon in system tray (bottom-right)
- Should say "Docker Desktop is running"

**Verify in Terminal:**
```powershell
docker --version
docker ps
```

---

## Need More Help?

If you encounter any issues:
1. Check the Docker Desktop logs (Settings → Troubleshoot → View logs)
2. Try restarting Docker Desktop
3. Try restarting your computer
4. Check Docker documentation: https://docs.docker.com/desktop/troubleshoot/overview/
