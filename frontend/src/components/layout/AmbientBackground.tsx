'use client';

/**
 * AmbientBackground — floating radial-gradient orbs with CSS animations.
 * Purely decorative, renders behind all content.
 */
export default function AmbientBackground() {
  return (
    <div className="ambient-bg" aria-hidden="true">
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />
    </div>
  );
}
