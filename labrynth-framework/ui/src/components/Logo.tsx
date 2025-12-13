export function LabyrinthLogo({ className = "w-8 h-8" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      className={className}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Greek key/meander pattern forming a labyrinth */}
      <defs>
        <linearGradient id="greekGold" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#D4AF37" />
          <stop offset="100%" stopColor="#B8860B" />
        </linearGradient>
        <linearGradient id="greekBlue" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#2C5F8D" />
          <stop offset="100%" stopColor="#1E4A7A" />
        </linearGradient>
      </defs>
      
      {/* Outer circle */}
      <circle cx="50" cy="50" r="48" fill="url(#greekBlue)" />
      
      {/* Greek key pattern labyrinth */}
      <g stroke="url(#greekGold)" strokeWidth="4" strokeLinecap="square" fill="none">
        {/* Outer layer */}
        <path d="M 25 25 L 75 25 L 75 75 L 25 75 L 25 35" />
        {/* Second layer */}
        <path d="M 35 35 L 65 35 L 65 65 L 35 65 L 35 45" />
        {/* Inner layer */}
        <path d="M 45 45 L 55 45 L 55 55 L 45 55 L 45 50" />
        {/* Center point */}
        <circle cx="50" cy="50" r="3" fill="url(#greekGold)" />
      </g>
      
      {/* Greek Lambda (Λ) subtle overlay */}
      <g opacity="0.3" fill="url(#greekGold)">
        <path d="M 50 30 L 40 55 L 45 55 L 50 42 L 55 55 L 60 55 Z" />
      </g>
    </svg>
  );
}

export function LabyrinthLogoSimple({ className = "w-6 h-6" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 100 100"
      className={className}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="simpleGold" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#D4AF37" />
          <stop offset="100%" stopColor="#B8860B" />
        </linearGradient>
      </defs>
      
      {/* Simplified labyrinth spiral */}
      <path
        d="M 50 10 L 50 30 L 70 30 L 70 70 L 30 70 L 30 40 L 60 40 L 60 60 L 40 60 L 40 50 L 50 50"
        stroke="url(#simpleGold)"
        strokeWidth="6"
        strokeLinecap="round"
        fill="none"
      />
      <circle cx="50" cy="50" r="4" fill="url(#simpleGold)" />
    </svg>
  );
}
