import { useThemeColors } from '../hooks/useThemeColors';

interface ThemeCardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
}

export function ThemeCard({ children, className = '', hover = false }: ThemeCardProps) {
  const { classes } = useThemeColors();
  
  return (
    <div className={`${classes.bgCard} border ${classes.borderCard} rounded-xl ${
      hover ? `${classes.bgHover} transition-all` : ''
    } ${className}`}>
      {children}
    </div>
  );
}
