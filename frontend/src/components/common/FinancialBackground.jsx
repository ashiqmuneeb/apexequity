import React, { useEffect, useRef } from 'react';

/**
 * Animated Matte White Financial & Neural Network Background
 * Features:
 * - Matte off-white canvas (#f8fafc)
 * - Animated neural synaptic network with floating nodes & connecting lines
 * - Action potential impulses traveling along synapses
 * - Soft animated financial equity/volume bars in the lower horizon
 * - Subtle ambient light gradients (Deep Navy #01257D & Electric Cyan #00FFFF / #00A3C4)
 */
export default function FinancialBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    // Mouse coordinates for gentle interactive field
    let mouse = { x: -1000, y: -1000, active: false };

    const handleResize = () => {
      if (!canvas) return;
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
      initNodes();
    };

    const handleMouseMove = (e) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
      mouse.active = true;
    };

    const handleMouseLeave = () => {
      mouse.active = false;
    };

    window.addEventListener('resize', handleResize);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseleave', handleMouseLeave);

    // Neural Nodes Configuration
    const NODE_COUNT = Math.min(Math.floor((width * height) / 22000), 55);
    const MAX_DISTANCE = 140;
    let nodes = [];
    let impulses = [];

    // Colors matching Deep Navy & Electric Cyan
    const PALETTE = [
      { r: 1, g: 37, b: 125 },    // Deep Navy #01257D
      { r: 0, g: 180, b: 216 },   // Electric Cyan
      { r: 2, g: 68, b: 201 },    // Vibrant Royal Blue
      { r: 14, g: 165, b: 233 },  // Sky Electric
    ];

    function initNodes() {
      nodes = [];
      const count = Math.min(Math.max(Math.floor((width * height) / 22000), 30), 65);
      for (let i = 0; i < count; i++) {
        const color = PALETTE[Math.floor(Math.random() * PALETTE.length)];
        nodes.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vx: (Math.random() - 0.5) * 0.45,
          vy: (Math.random() - 0.5) * 0.45,
          radius: 2 + Math.random() * 2.2,
          color,
          pulse: Math.random() * Math.PI * 2,
          pulseSpeed: 0.02 + Math.random() * 0.02,
        });
      }
    }

    initNodes();

    // Spawn occasional neural signal impulses traveling along synapses
    let lastImpulseTime = 0;

    let time = 0;

    function render(currentTime) {
      time += 0.015;
      ctx.clearRect(0, 0, width, height);

      // 1. Draw subtle background algorithmic/financial bars along bottom horizon
      const barCount = 38;
      const barWidth = width / barCount;
      const baseY = height - 10;

      for (let i = 0; i < barCount; i++) {
        // Multi-frequency sine waves creating organic undulating market bars
        const wave1 = Math.sin(time * 0.6 + i * 0.22);
        const wave2 = Math.cos(time * 0.4 + i * 0.35);
        const barHeight = 40 + (wave1 * 25 + wave2 * 18 + 25);
        const x = i * barWidth;
        const y = baseY - barHeight;

        // Alternate subtle navy and cyan washes with ultra-low opacity
        const isCyan = i % 3 === 0;
        ctx.fillStyle = isCyan
          ? `rgba(0, 180, 216, 0.038)`
          : `rgba(1, 37, 125, 0.032)`;

        ctx.fillRect(x + 2, y, barWidth - 4, barHeight);

        // Subtle bar top glow cap
        ctx.fillStyle = isCyan
          ? `rgba(0, 180, 216, 0.12)`
          : `rgba(1, 37, 125, 0.09)`;
        ctx.fillRect(x + 2, y, barWidth - 4, 1.5);
      }

      // 2. Update and draw Neural Network Nodes & Synaptic Connections
      // Update node positions
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];
        n.x += n.vx;
        n.y += n.vy;
        n.pulse += n.pulseSpeed;

        // Bounce gently against canvas boundaries
        if (n.x < 0) { n.x = 0; n.vx *= -1; }
        if (n.x > width) { n.x = width; n.vx *= -1; }
        if (n.y < 0) { n.y = 0; n.vy *= -1; }
        if (n.y > height) { n.y = height; n.vy *= -1; }

        // Subtle interactive mouse repulsion
        if (mouse.active) {
          const dx = n.x - mouse.x;
          const dy = n.y - mouse.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 120 && dist > 0) {
            const force = (120 - dist) / 120 * 0.8;
            n.x += (dx / dist) * force;
            n.y += (dy / dist) * force;
          }
        }
      }

      // Draw Synaptic Connection Lines
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const n1 = nodes[i];
          const n2 = nodes[j];
          const dx = n1.x - n2.x;
          const dy = n1.y - n2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < MAX_DISTANCE) {
            // Line opacity diminishes with distance
            const alpha = (1 - dist / MAX_DISTANCE) * 0.28;
            ctx.beginPath();
            ctx.moveTo(n1.x, n1.y);
            ctx.lineTo(n2.x, n2.y);

            // Subtle gradient line between nodes
            const grad = ctx.createLinearGradient(n1.x, n1.y, n2.x, n2.y);
            grad.addColorStop(0, `rgba(${n1.color.r}, ${n1.color.g}, ${n1.color.b}, ${alpha})`);
            grad.addColorStop(1, `rgba(${n2.color.r}, ${n2.color.g}, ${n2.color.b}, ${alpha})`);

            ctx.strokeStyle = grad;
            ctx.lineWidth = 1.1;
            ctx.stroke();

            // Randomly trigger impulses along close synapses
            if (currentTime - lastImpulseTime > 400 && Math.random() < 0.003 && impulses.length < 8) {
              impulses.push({
                from: n1,
                to: n2,
                progress: 0,
                speed: 0.015 + Math.random() * 0.02,
                color: n1.color,
              });
              lastImpulseTime = currentTime;
            }
          }
        }
      }

      // Draw Traveling Neural Impulses (Action Potentials)
      for (let i = impulses.length - 1; i >= 0; i--) {
        const imp = impulses[i];
        imp.progress += imp.speed;

        if (imp.progress >= 1) {
          impulses.splice(i, 1);
          continue;
        }

        const ix = imp.from.x + (imp.to.x - imp.from.x) * imp.progress;
        const iy = imp.from.y + (imp.to.y - imp.from.y) * imp.progress;

        ctx.beginPath();
        ctx.arc(ix, iy, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 180, 216, 0.85)`;
        ctx.shadowColor = 'rgba(0, 255, 255, 0.8)';
        ctx.shadowBlur = 6;
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      // Draw Neural Nodes (Neurons)
      for (let i = 0; i < nodes.length; i++) {
        const n = nodes[i];
        const pulseFactor = 1 + Math.sin(n.pulse) * 0.25;
        const currentRadius = n.radius * pulseFactor;

        // Outer glow halo
        ctx.beginPath();
        ctx.arc(n.x, n.y, currentRadius * 2.2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${n.color.r}, ${n.color.g}, ${n.color.b}, 0.08)`;
        ctx.fill();

        // Core neuron body
        ctx.beginPath();
        ctx.arc(n.x, n.y, currentRadius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${n.color.r}, ${n.color.g}, ${n.color.b}, 0.75)`;
        ctx.fill();

        // Inner bright nucleus
        ctx.beginPath();
        ctx.arc(n.x, n.y, currentRadius * 0.45, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
      }

      animationFrameId = requestAnimationFrame(render);
    }

    animationFrameId = requestAnimationFrame(render);

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseleave', handleMouseLeave);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0 bg-[#f8fafc]">
      {/* Soft Ambient Radial Light Washes */}
      <div className="absolute -top-32 left-1/4 w-[650px] h-[450px] bg-[#01257D]/[0.035] rounded-full blur-[140px]" />
      <div className="absolute -top-20 right-10 w-[550px] h-[380px] bg-[#00FFFF]/[0.045] rounded-full blur-[130px]" />
      <div className="absolute top-1/3 left-0 w-[450px] h-[450px] bg-[#0244c9]/[0.025] rounded-full blur-[140px]" />

      {/* HTML5 Canvas with Animated Neural Network & Financial Histogram Waves */}
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full block" />
    </div>
  );
}
