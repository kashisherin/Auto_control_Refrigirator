/**
 * refrigerator_3d.js
 *
 * Interactive visual representation of the industrial refrigerator.
 * Controls 3D door rotation, mist dissipation, temperature gradient lighting,
 * compressor fan spin state, and thermal flow visualization.
 */

class RefrigeratorVisualizer {
  constructor() {
    this.doorElement = document.getElementById('fridge-door');
    this.chamberElement = document.getElementById('fridge-chamber');
    this.fanElement = document.getElementById('compressor-fan');
    this.doorBtn = document.getElementById('door-toggle-btn');
    this.doorStatusText = document.getElementById('door-status-text');

    this.isOpen = false;
    this.initEventListeners();
  }

  initEventListeners() {
    if (this.doorElement) {
      this.doorElement.addEventListener('click', () => this.toggleDoor());
    }
  }

  setDoorState(isOpen) {
    this.isOpen = isOpen;
    if (this.doorElement) {
      if (isOpen) {
        this.doorElement.classList.add('open');
        this.chamberElement.classList.add('door-is-open');
      } else {
        this.doorElement.classList.remove('open');
        this.chamberElement.classList.remove('door-is-open');
      }
    }

    if (this.doorBtn) {
      if (isOpen) {
        this.doorBtn.className = 'door-toggle-btn is-open';
        this.doorBtn.innerHTML = '<span>🔒 CLOSE REFRIGERATOR DOOR</span>';
      } else {
        this.doorBtn.className = 'door-toggle-btn is-closed';
        this.doorBtn.innerHTML = '<span>🚪 OPEN REFRIGERATOR DOOR</span>';
      }
    }

    if (this.doorStatusText) {
      this.doorStatusText.textContent = isOpen ? 'DOOR OPEN (Heat Leak Active)' : 'DOOR CLOSED (Insulated)';
      this.doorStatusText.style.color = isOpen ? 'var(--accent-heat)' : 'var(--accent-success)';
    }
  }

  toggleDoor() {
    const newState = !this.isOpen;
    this.setDoorState(newState);

    // Trigger backend API door toggle call
    fetch('/api/door', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ door_open: newState })
    }).catch(err => console.error('Door toggle error:', err));
  }

  updateState(telemetry) {
    // 1. Synchronize door state from backend
    if (telemetry.door_open !== this.isOpen) {
      this.setDoorState(telemetry.door_open);
    }

    // 2. Dynamic Temperature Color Gradient
    const temp = telemetry.temperature_degc;
    const setpoint = telemetry.setpoint_degc;

    if (this.chamberElement) {
      if (temp > setpoint + 5.0 || telemetry.door_open) {
        this.chamberElement.className = `fridge-chamber warm ${this.isOpen ? 'door-is-open' : ''}`;
      } else {
        this.chamberElement.className = `fridge-chamber cold ${this.isOpen ? 'door-is-open' : ''}`;
      }
    }

    // 3. Compressor Fan spinning state
    if (this.fanElement) {
      if (telemetry.cooling_power_w > 10) {
        this.fanElement.classList.add('spinning');
      } else {
        this.fanElement.classList.remove('spinning');
      }
    }
  }
}

window.RefrigeratorVisualizer = RefrigeratorVisualizer;
