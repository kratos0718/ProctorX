const canvas = document.getElementById('neural-canvas');
if(canvas) {
    const ctx = canvas.getContext('2d');
    let width, height;
    let particles = [];

    function resize() {
        // use parent width
        const rect = canvas.parentElement.getBoundingClientRect();
        width = canvas.width = rect.width * 0.55; // 55% as per css
        height = canvas.height = rect.height;
    }
    window.addEventListener('resize', resize);
    resize();

    class Particle {
        constructor() {
            this.x = Math.random() * width;
            this.y = Math.random() * height;
            this.vx = (Math.random() - 0.5) * 0.8;
            this.vy = (Math.random() - 0.5) * 0.8;
            this.radius = Math.random() * 1.5 + 0.5;
        }
        update() {
            this.x += this.vx;
            this.y += this.vy;
            if (this.x < 0 || this.x > width) this.vx *= -1;
            if (this.y < 0 || this.y > height) this.vy *= -1;
        }
        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(99, 102, 241, 0.6)';
            ctx.fill();
        }
    }

    // initialize particles
    const particleCount = 45;
    for (let i = 0; i < particleCount; i++) {
        particles.push(new Particle());
    }

    function animate() {
        ctx.clearRect(0, 0, width, height);

        // draw connections
        for (let i = 0; i < particles.length; i++) {
            for (let j = i + 1; j < particles.length; j++) {
                const dx = particles[i].x - particles[j].x;
                const dy = particles[i].y - particles[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < 120) {
                    ctx.beginPath();
                    ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    const alpha = 1 - dist / 120;
                    ctx.strokeStyle = `rgba(34, 211, 238, ${alpha * 0.3})`;
                    ctx.lineWidth = 1;
                    ctx.stroke();
                }
            }
        }

        // update & draw particles
        for (let p of particles) {
            p.update();
            p.draw();
        }

        requestAnimationFrame(animate);
    }
    
    // Slight delay to ensure canvas bounds are settled
    setTimeout(animate, 100);
}
