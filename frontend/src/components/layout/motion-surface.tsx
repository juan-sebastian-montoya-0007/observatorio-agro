'use client';

import { useEffect, type ReactNode } from 'react';
import { MotionConfig, useAnimate, useReducedMotion } from 'motion/react';

const panels = '.kpi-card, .panel, .aq-card, .cmp-card, .cmp-kpi';

/** Animates newly mounted panels without remounting filters, maps or charts. */
export function MotionSurface({ children }: { children: ReactNode }) {
  const [scope, animate] = useAnimate<HTMLDivElement>();
  const reduced = useReducedMotion();

  useEffect(() => {
    const root = scope.current;
    if (!root || reduced) return;
    const seen = new WeakSet<Element>();
    const reveal = () => {
      const fresh = Array.from(root.querySelectorAll<HTMLElement>(panels)).filter(el => !seen.has(el));
      fresh.forEach((element, index) => {
        seen.add(element);
        void animate(element, { opacity: [0.65, 1], y: [10, 0] }, {
          duration: 0.35, delay: Math.min(index * 0.035, 0.18), ease: 'easeOut',
        });
      });
    };
    reveal();
    const observer = new MutationObserver(records => {
      if (records.some(record => Array.from(record.addedNodes).some(node =>
        node instanceof Element && (node.matches(panels) || node.querySelector(panels))
      ))) reveal();
    });
    observer.observe(root, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [animate, reduced, scope]);

  return <MotionConfig reducedMotion="user" transition={{ duration: 0.25, ease: 'easeOut' }}>
    <div ref={scope} className="motion-surface">{children}</div>
  </MotionConfig>;
}
