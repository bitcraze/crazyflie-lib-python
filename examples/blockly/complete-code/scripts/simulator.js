/**
 * Flight Path Simulator
 * Provides a 2D top-down visualization of drone flight paths
 */

class FlightSimulator {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');
    this.isAnimating = false;

    // Grid settings (in meters)
    this.gridSize = 10; // 10x10 meter grid (default to accommodate 3m movements)
    this.gridStep = 1.0; // 1.0m per grid line

    // Drone state
    this.droneX = 0; // meters
    this.droneY = 0; // meters
    this.droneZ = 0; // meters (height)
    this.droneYaw = 0; // degrees (0 = forward/north)
    this.droneColor = 'off'; // LED ring color
    this.isFlying = false;
    this.isOutOfBounds = false;

    // Animation settings
    this.animationSpeed = 1000; // ms per movement
    this.pathHistory = [];
    this.outOfBoundsWarned = false;

    // Set canvas size
    this.resizeCanvas();
    window.addEventListener('resize', () => this.resizeCanvas());
  }

  /**
   * Sets the grid size and redraws
   */
  setGridSize(size) {
    this.gridSize = size;
    this.gridStep = size <= 5 ? 0.5 : 1.0; // Larger grids use 1m steps
    this.reset();
  }

  /**
   * Checks if a position is within bounds
   */
  isPositionInBounds(x, y) {
    const halfGrid = this.gridSize / 2;
    return x >= -halfGrid && x <= halfGrid && y >= -halfGrid && y <= halfGrid;
  }

  resizeCanvas() {
    const container = this.canvas.parentElement;
    this.canvas.width = container.clientWidth;
    this.canvas.height = container.clientHeight;
    this.draw();
  }

  /**
   * Converts meters to canvas pixels
   */
  metersToPixels(meters) {
    // Use 68% of smallest dimension to leave room for labels
    const gridSizeInPixels = Math.min(this.canvas.width, this.canvas.height) * 0.60;
    return (meters / this.gridSize) * gridSizeInPixels;
  }

  /**
   * Gets the center point of the canvas
   */
  getCenter() {
    return {
      x: this.canvas.width / 2,
      y: (this.canvas.height / 2) - 20  // Shifted up by 10px
    };
  }

  /**
   * Converts drone coordinates to canvas coordinates
   * In Crazyflie: X=forward/back, Y=left/right
   * On canvas: X=left/right, Y=up/down
   */
  droneToCanvas(x, y) {
    const center = this.getCenter();
    return {
      x: center.x + this.metersToPixels(y), // Crazyflie Y (right+) → canvas X (right+)
      y: center.y - this.metersToPixels(x)  // Crazyflie X (forward+) → canvas Y (up+, flipped)
    };
  }

  /**
   * Draws the grid background
   */
  drawGrid() {
    this.ctx.strokeStyle = '#2a2a2a';
    this.ctx.lineWidth = 1;

    const center = this.getCenter();
    const halfGrid = this.gridSize / 2;

    // Draw grid lines
    for (let i = -halfGrid; i <= halfGrid; i += this.gridStep) {
      const offset = this.metersToPixels(i);

      // Vertical lines
      this.ctx.beginPath();
      this.ctx.moveTo(center.x + offset, center.y - this.metersToPixels(halfGrid));
      this.ctx.lineTo(center.x + offset, center.y + this.metersToPixels(halfGrid));
      this.ctx.stroke();

      // Horizontal lines
      this.ctx.beginPath();
      this.ctx.moveTo(center.x - this.metersToPixels(halfGrid), center.y + offset);
      this.ctx.lineTo(center.x + this.metersToPixels(halfGrid), center.y + offset);
      this.ctx.stroke();
    }

    // Draw center lines (axes) in brighter color
    this.ctx.strokeStyle = '#95C941';
    this.ctx.lineWidth = 2;

    // Y axis (vertical)
    this.ctx.beginPath();
    this.ctx.moveTo(center.x, center.y - this.metersToPixels(halfGrid));
    this.ctx.lineTo(center.x, center.y + this.metersToPixels(halfGrid));
    this.ctx.stroke();

    // X axis (horizontal)
    this.ctx.beginPath();
    this.ctx.moveTo(center.x - this.metersToPixels(halfGrid), center.y);
    this.ctx.lineTo(center.x + this.metersToPixels(halfGrid), center.y);
    this.ctx.stroke();

    // Draw axis labels
    this.ctx.fillStyle = '#95C941';
    this.ctx.font = '11px Courier New';

    // Forward label - top
    this.ctx.textAlign = 'center';
    this.ctx.textBaseline = 'bottom';
    this.ctx.fillText('↑ Forward', center.x, center.y - this.metersToPixels(halfGrid) - 10);

    // Back label - bottom
    this.ctx.textBaseline = 'top';
    this.ctx.fillText('↓ Back', center.x, center.y + this.metersToPixels(halfGrid) + 10);

    // Right label
    this.ctx.textAlign = 'left';
    this.ctx.textBaseline = 'middle';
    this.ctx.fillText('→ Right', center.x + this.metersToPixels(halfGrid) + 10, center.y);

    // Left label
    this.ctx.textAlign = 'right';
    this.ctx.fillText('Left ←', center.x - this.metersToPixels(halfGrid) - 10, center.y);
  }

  /**
   * Draws the path history
   */
  drawPath() {
    if (this.pathHistory.length < 2) return;

    this.ctx.strokeStyle = 'rgba(149, 201, 65, 0.5)';
    this.ctx.lineWidth = 3;
    this.ctx.lineCap = 'round';
    this.ctx.lineJoin = 'round';

    this.ctx.beginPath();
    const start = this.droneToCanvas(this.pathHistory[0].x, this.pathHistory[0].y);
    this.ctx.moveTo(start.x, start.y);

    for (let i = 1; i < this.pathHistory.length; i++) {
      const pos = this.droneToCanvas(this.pathHistory[i].x, this.pathHistory[i].y);
      this.ctx.lineTo(pos.x, pos.y);
    }

    this.ctx.stroke();

    // Draw dots at each position
    this.ctx.fillStyle = '#95C941';
    for (let i = 0; i < this.pathHistory.length; i++) {
      const pos = this.droneToCanvas(this.pathHistory[i].x, this.pathHistory[i].y);
      this.ctx.beginPath();
      this.ctx.arc(pos.x, pos.y, 4, 0, Math.PI * 2);
      this.ctx.fill();
    }
  }

  /**
   * Draws the drone
   */
  drawDrone() {
    const pos = this.droneToCanvas(this.droneX, this.droneY);

    // Drone body (circle)
    const size = 15;

    // Check if out of bounds
    this.isOutOfBounds = !this.isPositionInBounds(this.droneX, this.droneY);

    if (this.isOutOfBounds) {
      // Out of bounds - red with warning
      this.ctx.fillStyle = '#e74c3c';
      this.ctx.shadowColor = '#e74c3c';
      this.ctx.shadowBlur = 20;
    } else if (this.isFlying) {
      // Flying - green glow
      this.ctx.fillStyle = '#95C941';
      this.ctx.shadowColor = '#95C941';
      this.ctx.shadowBlur = 15;
    } else {
      // Grounded - gray
      this.ctx.fillStyle = '#666';
      this.ctx.shadowBlur = 0;
    }

    this.ctx.beginPath();
    this.ctx.arc(pos.x, pos.y, size, 0, Math.PI * 2);
    this.ctx.fill();

    // Reset shadow
    this.ctx.shadowBlur = 0;

    // LED ring visualization
    if (this.droneColor !== 'off') {
      const colorMap = {
        'red': '#FF0000',
        'green': '#00FF00',
        'blue': '#0000FF',
        'yellow': '#FFFF00',
        'purple': '#800080',
        'orange': '#FFA500',
        'cyan': '#00FFFF',
        'white': '#FFFFFF'
      };

      const ledColor = colorMap[this.droneColor] || '#FFFFFF';
      this.ctx.strokeStyle = ledColor;
      this.ctx.lineWidth = 4;
      this.ctx.shadowColor = ledColor;
      this.ctx.shadowBlur = 15;
      this.ctx.beginPath();
      this.ctx.arc(pos.x, pos.y, size + 5, 0, Math.PI * 2);
      this.ctx.stroke();
      this.ctx.shadowBlur = 0;
    }

    // Warning circle if out of bounds
    if (this.isOutOfBounds) {
      this.ctx.strokeStyle = '#e74c3c';
      this.ctx.lineWidth = 3;
      this.ctx.setLineDash([5, 5]);
      this.ctx.beginPath();
      this.ctx.arc(pos.x, pos.y, size + 8, 0, Math.PI * 2);
      this.ctx.stroke();
      this.ctx.setLineDash([]);
    }

    // Propeller lines
    if (this.isFlying) {
      this.ctx.strokeStyle = this.isOutOfBounds ? '#fff' : '#fff';
      this.ctx.lineWidth = 2;

      // Draw 4 propellers
      for (let i = 0; i < 4; i++) {
        const angle = (Math.PI / 2) * i + Math.PI / 4;
        const x1 = pos.x + Math.cos(angle) * size * 0.6;
        const y1 = pos.y + Math.sin(angle) * size * 0.6;
        const x2 = pos.x + Math.cos(angle) * size * 1.2;
        const y2 = pos.y + Math.sin(angle) * size * 1.2;

        this.ctx.beginPath();
        this.ctx.moveTo(x1, y1);
        this.ctx.lineTo(x2, y2);
        this.ctx.stroke();
      }
    }

    // Drone orientation indicator (forward direction) - rotates with yaw
    this.ctx.fillStyle = this.isOutOfBounds ? '#fff' : (this.isFlying ? '#fff' : '#444');

    // Convert yaw to radians (yaw is in degrees, 0 = up/north)
    const yawRad = (this.droneYaw - 90) * Math.PI / 180;

    // Triangle points before rotation
    const arrowLength = size + 8;
    const arrowWidth = 5;

    // Rotate the triangle around the drone center
    const cos = Math.cos(yawRad);
    const sin = Math.sin(yawRad);

    const tip = {
      x: pos.x + arrowLength * cos,
      y: pos.y + arrowLength * sin
    };
    const left = {
      x: pos.x + (size * cos - arrowWidth * sin),
      y: pos.y + (size * sin + arrowWidth * cos)
    };
    const right = {
      x: pos.x + (size * cos + arrowWidth * sin),
      y: pos.y + (size * sin - arrowWidth * cos)
    };

    this.ctx.beginPath();
    this.ctx.moveTo(tip.x, tip.y);
    this.ctx.lineTo(left.x, left.y);
    this.ctx.lineTo(right.x, right.y);
    this.ctx.closePath();
    this.ctx.fill();

    // Height indicator
    if (this.isFlying) {
      this.ctx.fillStyle = this.isOutOfBounds ? '#e74c3c' : '#95C941';
      this.ctx.font = '10px Courier New';
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'top';
      this.ctx.fillText(`${this.droneZ.toFixed(1)}m`, pos.x, pos.y + size + 8);
    }
  }

  /**
   * Main draw function
   */
  draw() {
    // Clear canvas
    this.ctx.fillStyle = '#1e1e1e';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    // Draw components
    this.drawGrid();
    this.drawPath();
    this.drawDrone();

    // Draw status text
    this.ctx.fillStyle = this.isOutOfBounds ? '#e74c3c' : '#95C941';
    this.ctx.font = '11px Courier New';
    this.ctx.textAlign = 'left';
    this.ctx.textBaseline = 'top';
    const status = this.isFlying ? 'FLYING' : 'GROUNDED';
    this.ctx.fillText(`Status: ${status}`, 8, 8);
    this.ctx.fillText(`Position: (${this.droneX.toFixed(1)}m, ${this.droneY.toFixed(1)}m)`, 8, 22);
    this.ctx.fillText(`LED: ${this.droneColor.toUpperCase()}`, 8, 36);

    // Out of bounds warning
    if (this.isOutOfBounds) {
      this.ctx.fillStyle = '#e74c3c';
      this.ctx.font = 'bold 13px Courier New';
      this.ctx.textAlign = 'center';
      this.ctx.textBaseline = 'top';
      this.ctx.fillText('⚠️ OUT OF BOUNDS ⚠️', this.canvas.width / 2, 10);
    }
  }

  /**
   * Resets the simulation
   */
  reset() {
    this.droneX = 0;
    this.droneY = 0;
    this.droneZ = 0;
    this.droneYaw = 0;
    this.droneColor = 'off';
    this.isFlying = false;
    this.isOutOfBounds = false;
    this.outOfBoundsWarned = false;
    this.pathHistory = [{x: 0, y: 0}];
    this.draw();
  }

  /**
   * Animates a movement
   */
  async animateMovement(fromX, fromY, toX, toY, duration) {
    const startTime = Date.now();
    const deltaX = toX - fromX;
    const deltaY = toY - fromY;

    return new Promise(resolve => {
      const animate = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Ease in-out
        const eased = progress < 0.5
          ? 2 * progress * progress
          : 1 - Math.pow(-2 * progress + 2, 2) / 2;

        this.droneX = fromX + deltaX * eased;
        this.droneY = fromY + deltaY * eased;

        this.draw();

        // Check if out of bounds and show warning
        if (!this.isPositionInBounds(this.droneX, this.droneY) && !this.outOfBoundsWarned) {
          this.outOfBoundsWarned = true;
          if (typeof showNotification === 'function') {
            showNotification('⚠️ Drone left the flight area!', 'warning');
          }
        }

        if (progress < 1) {
          requestAnimationFrame(animate);
        } else {
          this.pathHistory.push({x: toX, y: toY});
          resolve();
        }
      };

      animate();
    });
  }

  /**
   * Animates a rotation
   */
  async animateRotation(fromYaw, toYaw, duration) {
    const startTime = Date.now();
    const deltaYaw = toYaw - fromYaw;

    return new Promise(resolve => {
      const animate = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Ease in-out
        const eased = progress < 0.5
          ? 2 * progress * progress
          : 1 - Math.pow(-2 * progress + 2, 2) / 2;

        this.droneYaw = fromYaw + deltaYaw * eased;

        this.draw();

        if (progress < 1) {
          requestAnimationFrame(animate);
        } else {
          resolve();
        }
      };

      animate();
    });
  }

  /**
   * Animates a spiral movement
   */
  async animateSpiral(startX, startY, startZ, angle, startRadius, endRadius, ascent, clockwise, sideways, duration) {
    const startTime = Date.now();
    const startYaw = this.droneYaw;

    // Convert angle from degrees to radians
    const angleRad = angle * Math.PI / 180;

    // Direction multiplier
    const directionMult = clockwise ? -1 : 1;

    return new Promise(resolve => {
      const animate = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);

        // Ease in-out
        const eased = progress < 0.5
          ? 2 * progress * progress
          : 1 - Math.pow(-2 * progress + 2, 2) / 2;

        // Calculate current angle in the spiral
        const currentAngle = angleRad * eased;

        // Calculate current radius (interpolate between start and end)
        const currentRadius = startRadius + (endRadius - startRadius) * eased;

        // Calculate position relative to start
        // In Crazyflie frame: X=forward, Y=right
        // Spiral orientation depends on sideways parameter and current yaw

        const spiralYaw = startYaw * Math.PI / 180;

        if (sideways) {
          // Spiral in the Y-Z plane (sideways)
          const localY = currentRadius * Math.cos(currentAngle * directionMult);
          const localZ = currentRadius * Math.sin(currentAngle * directionMult);

          // Transform to world coordinates based on yaw
          this.droneX = startX - localY * Math.sin(spiralYaw);
          this.droneY = startY + localY * Math.cos(spiralYaw);
          this.droneZ = startZ + ascent * eased + (localZ - startRadius);
        } else {
          // Spiral in the X-Y plane (forward)
          const localX = currentRadius * Math.cos(currentAngle * directionMult);
          const localY = currentRadius * Math.sin(currentAngle * directionMult);

          // Transform to world coordinates based on yaw
          const worldDeltaX = (localX - startRadius) * Math.cos(spiralYaw) - localY * Math.sin(spiralYaw);
          const worldDeltaY = (localX - startRadius) * Math.sin(spiralYaw) + localY * Math.cos(spiralYaw);

          this.droneX = startX + worldDeltaX;
          this.droneY = startY + worldDeltaY;
          this.droneZ = startZ + ascent * eased;
        }

        // Add points to path history for visualization
        if (elapsed % 50 < 16) { // Add point roughly every 50ms
          this.pathHistory.push({x: this.droneX, y: this.droneY});
        }

        this.draw();

        // Check if out of bounds and show warning
        if (!this.isPositionInBounds(this.droneX, this.droneY) && !this.outOfBoundsWarned) {
          this.outOfBoundsWarned = true;
          if (typeof showNotification === 'function') {
            showNotification('⚠️ Drone left the flight area!', 'warning');
          }
        }

        if (progress < 1) {
          requestAnimationFrame(animate);
        } else {
          this.pathHistory.push({x: this.droneX, y: this.droneY});
          resolve();
        }
      };

      animate();
    });
  }

  /**
   * Executes a command
   */
  async executeCommand(command) {
    const fromX = this.droneX;
    const fromY = this.droneY;

    // Convert current yaw to radians for trigonometry
    const yawRad = this.droneYaw * Math.PI / 180;

    switch (command.type) {
      case 'takeoff':
        this.isFlying = true;
        this.droneZ = 1.0;
        await new Promise(resolve => setTimeout(resolve, 500));
        this.draw();
        break;

      case 'land':
        this.isFlying = false;
        this.droneZ = 0;
        await new Promise(resolve => setTimeout(resolve, 500));
        this.draw();
        break;

      case 'forward':
        const forwardDistance = command.distance || 0.5;
        // Move in the direction the drone is facing
        const forwardDeltaX = forwardDistance * Math.cos(yawRad);
        const forwardDeltaY = forwardDistance * Math.sin(yawRad);
        await this.animateMovement(fromX, fromY, fromX + forwardDeltaX, fromY + forwardDeltaY, this.animationSpeed);
        break;

      case 'back':
        const backDistance = command.distance || 0.5;
        // Move opposite to the direction the drone is facing
        const backDeltaX = -backDistance * Math.cos(yawRad);
        const backDeltaY = -backDistance * Math.sin(yawRad);
        await this.animateMovement(fromX, fromY, fromX + backDeltaX, fromY + backDeltaY, this.animationSpeed);
        break;

      case 'left':
        const leftDistance = command.distance || 0.5;
        // Move 90° counter-clockwise from facing direction
        const leftDeltaX = -leftDistance * Math.sin(yawRad);
        const leftDeltaY = leftDistance * Math.cos(yawRad);
        await this.animateMovement(fromX, fromY, fromX + leftDeltaX, fromY + leftDeltaY, this.animationSpeed);
        break;

      case 'right':
        const rightDistance = command.distance || 0.5;
        // Move 90° clockwise from facing direction
        const rightDeltaX = rightDistance * Math.sin(yawRad);
        const rightDeltaY = -rightDistance * Math.cos(yawRad);
        await this.animateMovement(fromX, fromY, fromX + rightDeltaX, fromY + rightDeltaY, this.animationSpeed);
        break;

      case 'rotate':
        const angle = command.angle || 90;
        const direction = command.direction || 'cw';
        const rotationChange = direction === 'cw' ? -angle : angle;
        const fromYaw = this.droneYaw;
        const toYaw = this.droneYaw + rotationChange;
        await this.animateRotation(fromYaw, toYaw, this.animationSpeed);
        break;

      case 'spiral':
        const spiralAngle = command.angle || 360;
        const spiralDirection = command.direction || 'ccw';
        const startRadius = command.startRadius || 0.5;
        const endRadius = command.endRadius || 1.0;
        const ascent = command.ascent || 0.0;
        const sideways = command.sideways || false;
        const clockwise = spiralDirection === 'cw';

        // Calculate animation duration based on spiral length
        const avgRadius = (startRadius + endRadius) / 2;
        const arcLength = avgRadius * spiralAngle * Math.PI / 180;
        const spiralDuration = this.animationSpeed * (arcLength / 0.5) * 2; // Adjust multiplier for visual speed

        await this.animateSpiral(
          fromX, fromY, this.droneZ,
          spiralAngle, startRadius, endRadius, ascent,
          clockwise, sideways, spiralDuration
        );
        break;

      case 'altitude':
        const altDistance = command.distance || 0.5;
        const altDirection = command.direction || 'up';
        const zChange = altDirection === 'up' ? altDistance : -altDistance;
        this.droneZ += zChange;
        await new Promise(resolve => setTimeout(resolve, this.animationSpeed));
        this.draw();
        break;

      case 'led_color':
        this.droneColor = command.color || 'off';
        this.draw();
        break;
    }
  }

  /**
   * Runs a complete flight simulation
   */
  async simulate(commands) {
    if (this.isAnimating) return;

    this.isAnimating = true;
    this.outOfBoundsWarned = false;
    this.reset();

    for (const command of commands) {
      await this.executeCommand(command);
    }

    this.isAnimating = false;
  }
}

// Initialize simulator when DOM is ready
let flightSimulator;
document.addEventListener('DOMContentLoaded', () => {
  flightSimulator = new FlightSimulator('simulatorCanvas');

  // Connect grid size selector
  const gridSizeSelect = document.getElementById('gridSizeSelect');
  if (gridSizeSelect) {
    gridSizeSelect.addEventListener('change', (e) => {
      const size = parseInt(e.target.value);
      flightSimulator.setGridSize(size);
    });
  }
});
