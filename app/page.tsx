'use client';

import React, { useState } from 'react';
import Link from 'next/link';

export default function Home() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="cozy-landing-body">
      {/* Navigation */}
      <header className="cozy-navbar" role="banner">
        <div className="cozy-nav-inner">
          <a href="/landing" className="cozy-brand" aria-label="StudyTracker Home">
            <div className="cozy-brand-icon" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/>
                <path d="M6 6h10"/>
                <path d="M6 10h10"/>
                <path d="M6 14h6"/>
              </svg>
            </div>
            <span>StudyTracker</span>
          </a>

          <nav className="cozy-nav-links" aria-label="Main Navigation">
            <a href="#preview" className="cozy-nav-link">Preview</a>
            <a href="#how-it-works" className="cozy-nav-link">How it works</a>
            <a href="#features" className="cozy-nav-link">Features</a>
          </nav>

          <div className="cozy-nav-actions">
            <a href="/login" className="btn-cozy-text">Sign in</a>
            <a href="/register" className="btn-cozy-primary">Start studying</a>
          </div>

          <button
            type="button"
            className="cozy-nav-toggle"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle navigation menu"
            aria-expanded={mobileMenuOpen}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="12" x2="21" y2="12"/>
              <line x1="3" y1="6" x2="21" y2="6"/>
              <line x1="3" y1="18" x2="21" y2="18"/>
            </svg>
          </button>
        </div>

        {mobileMenuOpen && (
          <div className="cozy-nav-mobile open">
            <nav className="cozy-nav-links" aria-label="Mobile Navigation">
              <a href="#preview" className="cozy-nav-link" onClick={() => setMobileMenuOpen(false)}>Preview</a>
              <a href="#how-it-works" className="cozy-nav-link" onClick={() => setMobileMenuOpen(false)}>How it works</a>
              <a href="#features" className="cozy-nav-link" onClick={() => setMobileMenuOpen(false)}>Features</a>
            </nav>
            <div className="cozy-nav-actions">
              <a href="/login" className="btn-cozy-text">Sign in</a>
              <a href="/register" className="btn-cozy-primary">Start studying</a>
            </div>
          </div>
        )}
      </header>

      <main id="main-content">
        {/* HERO SECTION */}
        <section className="cozy-hero" aria-labelledby="hero-title">
          <div className="cozy-container">
            <div className="hero-grid">
              <div className="hero-content">
                <div className="hero-badge">
                  <span className="hero-badge-dot"></span>
                  <span>A quiet space for your study craft</span>
                </div>
                
                <h1 id="hero-title" className="hero-title">
                  Make space for your <br />
                  <span className="highlight-rose">next little win.</span>
                </h1>
                
                <p className="hero-subtitle">
                  A calmer way to plan your study sessions, track your progress, and celebrate how far you’ve come.
                </p>
                
                <div className="hero-cta-group">
                  <a href="/register" className="btn-hero-primary">
                    <span>Start studying for free</span>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="5" y1="12" x2="19" y2="12"/>
                      <polyline points="12 5 19 12 12 19"/>
                    </svg>
                  </a>
                  <a href="#how-it-works" className="btn-hero-secondary">See how it works</a>
                </div>
                
                <div className="hero-microcopy">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#919D85" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                  </svg>
                  <span>No clutter, no distractions · Free to start</span>
                </div>
              </div>

              {/* Hero Visual Card with Mascot */}
              <div className="hero-visual-card">
                <div className="mascot-stage" aria-label="Study Companion Mascot">
                  <div className="mascot-bubble">
                    <span>Ready to focus today? ✨</span>
                  </div>

                  <div className="mascot-figure-wrapper" title="Say hello to your study companion!">
                    <div className="mascot-heart-particle" aria-hidden="true">
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="#C496A1">
                        <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/>
                      </svg>
                    </div>

                    <svg className="mascot-svg" viewBox="0 0 160 160" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Cute lavender study companion blob">
                      <path d="M80 32C76 20 64 22 64 22C64 22 66 34 78 35" stroke="#919D85" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" fill="#EDF1EB"/>
                      <path d="M80 32C84 20 96 22 96 22C96 22 94 34 82 35" stroke="#919D85" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" fill="#919D85"/>
                      <path d="M80 36C45 36 32 60 32 94C32 126 50 144 80 144C110 144 128 126 128 94C128 60 115 36 80 36Z" fill="#8E88A3"/>
                      <path d="M48 110C56 130 68 138 80 138C92 138 104 130 112 110C98 116 62 116 48 110Z" fill="#7D7694" opacity="0.35"/>
                      <circle cx="54" cy="94" r="7" fill="#C496A1" opacity="0.85"/>
                      <circle cx="106" cy="94" r="7" fill="#C496A1" opacity="0.85"/>
                      <g className="mascot-eye">
                        <ellipse cx="62" cy="84" rx="4.5" ry="6" fill="#2D282E"/>
                        <circle cx="60.5" cy="82" r="1.8" fill="#FFFFFF"/>
                        <ellipse cx="98" cy="84" rx="4.5" ry="6" fill="#2D282E"/>
                        <circle cx="96.5" cy="82" r="1.8" fill="#FFFFFF"/>
                      </g>
                      <path d="M74 94C77 98 83 98 86 94" stroke="#2D282E" strokeWidth="2.5" strokeLinecap="round"/>
                      <rect x="114" y="90" width="8" height="24" rx="2" transform="rotate(25 114 90)" fill="#EBE1C6" stroke="#2D282E" strokeWidth="1.5"/>
                      <polygon points="124,112 120,119 117,114" fill="#C496A1" stroke="#2D282E" strokeWidth="1.2"/>
                      <path d="M112 98C118 96 122 100 120 106" stroke="#8E88A3" strokeWidth="6" strokeLinecap="round"/>
                    </svg>
                  </div>
                  
                  <div className="mascot-shadow" aria-hidden="true"></div>
                </div>

                <div className="hero-mini-tracker">
                  <div className="mini-tracker-row">
                    <span className="mini-tracker-pill">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                      <span>Today's Deep Work</span>
                    </span>
                    <span className="mini-tracker-time">3h 45m</span>
                  </div>
                  <div className="mini-progress-bar">
                    <div className="mini-progress-fill" style={{ width: '78%' }}></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* PRODUCT PREVIEW */}
        <section id="preview" className="cozy-section" aria-labelledby="preview-heading">
          <div className="cozy-container">
            <div className="section-header">
              <span className="section-tag">Study Journal Snapshot</span>
              <h2 id="preview-heading" className="section-title">Designed like your favorite desk notebook.</h2>
              <p className="section-desc">Every feature connects to your actual study craft—without the overwhelm of complex project management tools.</p>
            </div>

            <div className="journal-desk-card">
              <div className="journal-header">
                <div className="journal-title-box">
                  <div className="journal-icon-badge">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
                    </svg>
                  </div>
                  <div>
                    <h3 className="journal-heading">Daily Study Session</h3>
                    <span className="journal-date">Today · Focus &amp; Reflection</span>
                  </div>
                </div>
                <div className="journal-streak-pill">
                  <span>🔥 14-Day Active Streak</span>
                </div>
              </div>

              <div className="journal-grid">
                {/* Focus Ring Timer */}
                <div className="journal-panel">
                  <div className="panel-label">
                    <span>Focus Timer</span>
                    <span style={{ color: 'var(--color-muted-sage)' }}>25 min block</span>
                  </div>
                  <div className="timer-ring-wrap">
                    <div className="timer-svg-container">
                      <svg className="timer-svg" viewBox="0 0 140 140">
                        <circle className="timer-ring-bg" cx="70" cy="70" r="60"/>
                        <circle className="timer-ring-progress" cx="70" cy="70" r="60"/>
                      </svg>
                      <div className="timer-digits-overlay">18:42</div>
                    </div>
                    <div className="timer-current-task">Calculus · Problem Set 4</div>
                    <span className="timer-subject-tag">Mathematics</span>
                  </div>
                </div>

                {/* 7-Day Velocity */}
                <div className="journal-panel">
                  <div className="panel-label">
                    <span>7-Day Study Velocity</span>
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--color-charcoal)' }}>16.5 hrs</span>
                  </div>
                  <div className="velocity-chart-wrap">
                    <div className="velocity-bars-row">
                      <div className="v-bar-col">
                        <div className="v-bar" style={{ height: '45%' }} title="Mon: 1h 30m"></div>
                        <span className="v-day">M</span>
                      </div>
                      <div className="v-bar-col">
                        <div className="v-bar high" style={{ height: '80%' }} title="Tue: 3h 15m"></div>
                        <span className="v-day">T</span>
                      </div>
                      <div className="v-bar-col">
                        <div className="v-bar" style={{ height: '60%' }} title="Wed: 2h 00m"></div>
                        <span className="v-day">W</span>
                      </div>
                      <div className="v-bar-col">
                        <div className="v-bar high" style={{ height: '90%' }} title="Thu: 3h 45m"></div>
                        <span className="v-day">T</span>
                      </div>
                      <div className="v-bar-col">
                        <div className="v-bar" style={{ height: '50%' }} title="Fri: 1h 45m"></div>
                        <span className="v-day">F</span>
                      </div>
                      <div className="v-bar-col">
                        <div className="v-bar high" style={{ height: '75%' }} title="Sat: 2h 30m"></div>
                        <span className="v-day">S</span>
                      </div>
                      <div className="v-bar-col">
                        <div className="v-bar today" style={{ height: '85%' }} title="Today: 3h 00m"></div>
                        <span className="v-day">Sun</span>
                      </div>
                    </div>
                    <div className="subject-pills-row">
                      <span className="subj-pill"><span className="subj-dot" style={{ background: 'var(--color-dusty-rose)' }}></span>Physics</span>
                      <span className="subj-pill"><span className="subj-dot" style={{ background: 'var(--color-muted-sage)' }}></span>Calculus</span>
                      <span className="subj-pill"><span className="subj-dot" style={{ background: 'var(--color-lavender-purple)' }}></span>Literature</span>
                    </div>
                  </div>
                </div>

                {/* Tasks & Reflection */}
                <div className="journal-panel">
                  <div className="panel-label">
                    <span>Checklist &amp; Notes</span>
                    <span style={{ color: 'var(--color-dusty-rose)' }}>2 of 3 done</span>
                  </div>
                  <div className="tasks-list">
                    <div className="task-item completed">
                      <div className="task-check done">✓</div>
                      <span>Review Chapter 4 summary</span>
                    </div>
                    <div className="task-item completed">
                      <div className="task-check done">✓</div>
                      <span>Complete flashcard deck</span>
                    </div>
                    <div className="task-item">
                      <div className="task-check"></div>
                      <span>Solve 3 practice problems</span>
                    </div>
                  </div>
                  <div className="sticky-encouragement">
                    "Consistency over perfection. You are doing wonderful!"
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* HOW IT WORKS */}
        <section id="how-it-works" className="cozy-section" aria-labelledby="steps-heading">
          <div className="cozy-container">
            <div className="section-header">
              <span className="section-tag">Gentle Workflow</span>
              <h2 id="steps-heading" className="section-title">How StudyTracker works for you</h2>
              <p className="section-desc">Three simple steps to cultivate deep study habits and keep your momentum alive.</p>
            </div>

            <div className="steps-grid">
              <div className="step-card">
                <div className="step-number-badge">01</div>
                <h3 className="step-title">Organize what you study</h3>
                <p className="step-desc">Create your subjects with customized color badges, organize assignments, and set semester target hour goals.</p>
              </div>

              <div className="step-card">
                <div className="step-number-badge">02</div>
                <h3 className="step-title">Track your study sessions</h3>
                <p className="step-desc">Log exact minutes, write down key takeaways and notes, and record past sessions with intuitive date controls.</p>
              </div>

              <div className="step-card">
                <div className="step-number-badge">03</div>
                <h3 className="step-title">Celebrate consistency</h3>
                <p className="step-desc">Watch your 7-day velocity chart, see your active streak count grow, and view your 16-week study activity heatmap.</p>
              </div>
            </div>
          </div>
        </section>

        {/* FEATURE HIGHLIGHTS */}
        <section id="features" className="cozy-section" aria-labelledby="features-heading">
          <div className="cozy-container">
            <div className="section-header">
              <span className="section-tag">Feature Highlights</span>
              <h2 id="features-heading" className="section-title">Everything you need for disciplined focus</h2>
              <p className="section-desc">Built for students and self-learners who appreciate calm, intentional tools.</p>
            </div>

            <div className="features-grid">
              <div className="feature-box">
                <div className="feature-icon-wrapper">
                  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                  </svg>
                </div>
                <h3 className="feature-title">Distraction-Free Session Logging</h3>
                <p className="feature-desc">Record deep focus sessions with custom titles, durations, subject categorization, and rich notes for every session.</p>
                <div className="feature-pill-list">
                  <span className="feature-pill">Session notes</span>
                  <span className="feature-pill">Past date logging</span>
                  <span className="feature-pill">Quick edit &amp; delete</span>
                </div>
              </div>

              <div className="feature-box">
                <div className="feature-icon-wrapper">
                  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>
                  </svg>
                </div>
                <h3 className="feature-title">7-Day Velocity &amp; Breakdown</h3>
                <p className="feature-desc">Visualize your daily study minutes across the past 7 days and see exactly how your effort distributes across subjects.</p>
                <div className="feature-pill-list">
                  <span className="feature-pill">7-day bar chart</span>
                  <span className="feature-pill">Daily averages</span>
                  <span className="feature-pill">Subject distribution</span>
                </div>
              </div>

              <div className="feature-box">
                <div className="feature-icon-wrapper">
                  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
                  </svg>
                </div>
                <h3 className="feature-title">Milestone Target Goals</h3>
                <p className="feature-desc">Set target hours for exam preps or semesters. Track real-time progress bars and stay motivated until completion.</p>
                <div className="feature-pill-list">
                  <span className="feature-pill">Hour targets</span>
                  <span className="feature-pill">Dynamic progress</span>
                  <span className="feature-pill">Milestone badges</span>
                </div>
              </div>

              <div className="feature-box">
                <div className="feature-icon-wrapper">
                  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
                  </svg>
                </div>
                <h3 className="feature-title">Weekly Calendar &amp; Activity Heatmap</h3>
                <p className="feature-desc">Browse through your week-by-week calendar timeline and discover patterns in your 16-week study activity grid.</p>
                <div className="feature-pill-list">
                  <span className="feature-pill">Weekly view</span>
                  <span className="feature-pill">16-week heatmap</span>
                  <span className="feature-pill">Daily intensity</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* FINAL CALL TO ACTION */}
        <section className="cozy-section" aria-label="Get Started">
          <div className="cozy-container">
            <div className="final-cta-card">
              <div className="final-cta-mascot" aria-hidden="true">
                <svg viewBox="0 0 120 120" fill="none">
                  <path d="M60 20C36 20 25 40 25 65C25 90 40 102 60 102C80 102 95 90 95 65C95 40 84 20 60 20Z" fill="#8E88A3"/>
                  <circle cx="43" cy="65" r="5" fill="#C496A1" opacity="0.8"/>
                  <circle cx="77" cy="65" r="5" fill="#C496A1" opacity="0.8"/>
                  <ellipse cx="48" cy="58" rx="3.5" ry="4.5" fill="#2D282E"/>
                  <circle cx="47" cy="56" r="1.3" fill="#FFFFFF"/>
                  <ellipse cx="72" cy="58" rx="3.5" ry="4.5" fill="#2D282E"/>
                  <circle cx="71" cy="56" r="1.3" fill="#FFFFFF"/>
                  <path d="M55 65C58 68 62 68 65 65" stroke="#2D282E" strokeWidth="2" strokeLinecap="round"/>
                  <path d="M60 18C57 10 48 12 48 12C48 12 50 20 58 20" stroke="#919D85" strokeWidth="2.5" strokeLinecap="round" fill="#919D85"/>
                </svg>
              </div>

              <h2 className="final-cta-title">Little by little, you’re getting there.</h2>
              <p className="final-cta-subtitle">Your next study session is a fresh start. Set up your cozy personal study space today.</p>
              
              <div className="final-cta-actions">
                <a href="/register" className="btn-hero-primary">
                  <span>Create your study space</span>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="5" y1="12" x2="19" y2="12"/>
                    <polyline points="12 5 19 12 12 19"/>
                  </svg>
                </a>
                <a href="/login" className="btn-hero-secondary">Sign in to existing space</a>
              </div>

              <p className="final-cta-note">No credit card required · Start tracking in seconds</p>
            </div>
          </div>
        </section>
      </main>

      {/* FOOTER */}
      <footer className="cozy-footer" role="contentinfo">
        <div className="cozy-container">
          <div className="footer-top">
            <a href="/landing" className="cozy-brand" aria-label="StudyTracker Home">
              <div className="cozy-brand-icon" aria-hidden="true" style={{ width: '32px', height: '32px' }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/>
                  <path d="M6 6h10"/>
                  <path d="M6 10h10"/>
                  <path d="M6 14h6"/>
                </svg>
              </div>
              <span>StudyTracker</span>
            </a>

            <ul className="footer-links">
              <li><a href="#preview" className="footer-link">Preview</a></li>
              <li><a href="#how-it-works" className="footer-link">How it works</a></li>
              <li><a href="#features" className="footer-link">Features</a></li>
              <li><a href="/login" className="footer-link">Sign in</a></li>
              <li><a href="/register" className="footer-link">Register</a></li>
            </ul>
          </div>

          <div className="footer-bottom">
            <span>© StudyTracker · Crafted with care for calm, disciplined focus.</span>
            <span>Fixed Palette: Vintage Cream, Dusty Rose, Muted Sage &amp; Lavender.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
