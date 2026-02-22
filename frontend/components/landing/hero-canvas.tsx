"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

export function HeroCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      75,
      container.clientWidth / container.clientHeight,
      0.1,
      1000,
    );
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    const count = 1500;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);

    for (let i = 0; i < count * 3; i++) {
      positions[i] = (Math.random() - 0.5) * 20;
    }

    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));

    const material = new THREE.PointsMaterial({
      size: 0.03,
      color: 0xffffff,
      transparent: true,
      opacity: 0.8,
    });

    const particles = new THREE.Points(geometry, material);
    scene.add(particles);
    camera.position.z = 5;

    let time = 0;
    let animationId: number;

    const animate = () => {
      animationId = requestAnimationFrame(animate);
      time += 0.002;

      const pos = particles.geometry.attributes.position
        .array as Float32Array;

      for (let i = 0; i < count; i++) {
        const i3 = i * 3;
        pos[i3 + 1] += Math.sin(time + pos[i3]) * 0.002;
      }

      particles.rotation.y = time * 0.2;
      particles.rotation.x = time * 0.1;
      particles.geometry.attributes.position.needsUpdate = true;
      renderer.render(scene, camera);
    };

    animate();

    const onResize = () => {
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    };

    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener("resize", onResize);
      renderer.dispose();
      geometry.dispose();
      material.dispose();
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="absolute top-0 left-0 w-full h-full z-0 pointer-events-none"
    />
  );
}
