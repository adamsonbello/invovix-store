import React from "react";
import { Star } from "lucide-react";

export function Stars({ value = 0, size = 16, className = "" }) {
  return (
    <div className={`flex ${className}`} aria-label={`${value} / 5`}>
      {[1, 2, 3, 4, 5].map((i) => (
        <Star
          key={i}
          className="shrink-0"
          style={{ width: size, height: size }}
          fill={i <= Math.round(value) ? "#FF3300" : "none"}
          stroke={i <= Math.round(value) ? "#FF3300" : "#cfcfcf"}
          strokeWidth={1.5}
        />
      ))}
    </div>
  );
}

export function StarInput({ value, onChange, size = 26, testid }) {
  return (
    <div className="flex gap-1.5" data-testid={testid}>
      {[1, 2, 3, 4, 5].map((i) => (
        <button type="button" key={i} onClick={() => onChange(i)} aria-label={`${i} stars`} data-testid={`${testid}-${i}`}>
          <Star
            style={{ width: size, height: size }}
            fill={i <= value ? "#FF3300" : "none"}
            stroke={i <= value ? "#FF3300" : "#999"}
            strokeWidth={1.5}
            className="hover:scale-110 transition-transform"
          />
        </button>
      ))}
    </div>
  );
}
