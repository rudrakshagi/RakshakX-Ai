import React from 'react';

interface LogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  withText?: boolean;
}

export const Logo: React.FC<LogoProps> = ({
  className = '',
  size = 'md',
  withText = true,
}) => {
  const sizeMap = {
    sm: { img: 'h-8', text: 'text-sm' },
    md: { img: 'h-9', text: 'text-base' },
    lg: { img: 'h-12', text: 'text-xl' },
    xl: { img: 'h-16', text: 'text-2xl' },
  };

  const currentSize = sizeMap[size];

  return (
    <div className={`flex items-center gap-2.5 select-none ${className}`}>
      {/* Official Branded Emblem */}
      <div className={`relative ${currentSize.img} aspect-square rounded-xl overflow-hidden shadow-xs border border-slate-200/80 dark:border-slate-700 bg-white shrink-0 transition-transform duration-200 hover:scale-105 p-0.5`}>
        <img
          src="/logo.png"
          alt="RakshakX Official Logo"
          className="w-full h-full object-contain"
        />
      </div>

      {/* Brand Wordmark Typography */}
      {withText && (
        <div className="flex flex-col tracking-tight leading-none">
          <span className={`font-extrabold text-slate-900 dark:text-white ${currentSize.text} tracking-tight`}>
            Rakshak<span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-cyan-500">X</span>
          </span>
          <span className="text-[9px] font-mono uppercase tracking-widest text-slate-400 dark:text-slate-500 font-semibold mt-0.5">
            Security Intelligence
          </span>
        </div>
      )}
    </div>
  );
};
