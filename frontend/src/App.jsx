import React, { useState, useEffect } from 'react';
import Header from './components/common/Header';
import StatusBanner from './components/common/StatusBanner';
import ApiKeyModal from './components/common/ApiKeyModal';
import OnboardingModal from './components/common/OnboardingModal';
import CommandPalette from './components/common/CommandPalette';
import TickerTape from './components/common/TickerTape';
import FinancialBackground from './components/common/FinancialBackground';
import TabNavigation from './components/layout/TabNavigation';
import Footer from './components/layout/Footer';
import SingleStockView from './features/singleStock/SingleStockView';
import ComparisonView from './features/comparison/ComparisonView';
import CustomQueryView from './features/customQuery/CustomQueryView';
import ArticleManager from './features/articles/ArticleManager';
import { useSystemStatus } from './hooks/useSystemStatus';
import { TABS } from './constants/stockTickers';

export default function App() {
  const [activeTab, setActiveTab] = useState(TABS.SINGLE);
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [customQueryInitialPrompt, setCustomQueryInitialPrompt] = useState('');

  // Global Ctrl+K / Cmd+K shortcut listener
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Check if first-time visitor
  useEffect(() => {
    const hasVisited = localStorage.getItem('apex_onboarding_seen');
    if (!hasVisited) {
      setIsOnboardingOpen(true);
    }
  }, []);

  const handleCloseOnboarding = () => {
    setIsOnboardingOpen(false);
    localStorage.setItem('apex_onboarding_seen', 'true');
  };

  const handleNavigateCustom = (query) => {
    setCustomQueryInitialPrompt(query);
    setActiveTab(TABS.CUSTOM);
  };

  const {
    status,
    isKeyModalOpen,
    setIsKeyModalOpen,
    isRebuilding,
    rebuildFeedback,
    fetchStatus,
    saveGroqKey,
    rebuildIndex,
  } = useSystemStatus();

  return (
    <div className="finance-bg relative min-h-screen bg-[#f8fafc] text-slate-800 flex flex-col font-sans overflow-x-hidden">
      
      {/* Dynamic Ambient Financial Chart & Glow Waves */}
      <FinancialBackground />

      {/* Financial Market Ticker Ribbon */}
      <div className="relative z-20">
        <TickerTape onSelectTicker={(ticker) => setActiveTab(TABS.SINGLE)} />
      </div>

      {/* Top Header */}
      <div className="relative z-20">
        <Header
          status={status}
          onOpenKeyModal={() => setIsKeyModalOpen(true)}
          onRebuildIndex={rebuildIndex}
          isRebuilding={isRebuilding}
          onOpenTour={() => setIsOnboardingOpen(true)}
          onOpenCommandPalette={() => setIsCommandPaletteOpen(true)}
        />
      </div>

      {/* Warning/Action Banners */}
      <div className="relative z-20">
        <StatusBanner
          status={status}
          onOpenKeyModal={() => setIsKeyModalOpen(true)}
          onRebuildIndex={rebuildIndex}
          isRebuilding={isRebuilding}
        />
      </div>

      {/* Floating Rebuild Alert */}
      {rebuildFeedback && (
        <div
          className={`relative z-20 py-2 px-4 text-center text-xs font-semibold ${
            rebuildFeedback.type === 'success'
              ? 'bg-emerald-500/20 text-emerald-300'
              : 'bg-red-500/20 text-red-300'
          }`}
        >
          {rebuildFeedback.text}
        </div>
      )}

      {/* Main Container */}
      <main className="relative z-10 flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        
        {/* Navigation Tabs */}
        <TabNavigation
          activeTab={activeTab}
          onTabChange={setActiveTab}
          articleCount={status?.indexed_articles_count || 0}
        />

        {/* Tab Views */}
        <div>
          {activeTab === TABS.SINGLE && (
            <SingleStockView
              availableTickers={status?.articles}
              onOpenKeyModal={() => setIsKeyModalOpen(true)}
              onNavigateCustom={handleNavigateCustom}
            />
          )}

          {activeTab === TABS.COMPARE && (
            <ComparisonView
              availableTickers={status?.articles}
              onOpenKeyModal={() => setIsKeyModalOpen(true)}
            />
          )}

          {activeTab === TABS.CUSTOM && (
            <CustomQueryView
              onOpenKeyModal={() => setIsKeyModalOpen(true)}
              initialPrompt={customQueryInitialPrompt}
            />
          )}

          {activeTab === TABS.ARTICLES && (
            <ArticleManager
              onRebuildIndex={rebuildIndex}
              isRebuilding={isRebuilding}
              onCorpusChange={fetchStatus}
            />
          )}
        </div>

      </main>

      {/* Footer */}
      <div className="relative z-20">
        <Footer />
      </div>

      {/* Groq API Key Configuration Modal */}
      <ApiKeyModal
        isOpen={isKeyModalOpen}
        onClose={() => setIsKeyModalOpen(false)}
        onSaveKey={saveGroqKey}
        currentHasKey={status?.has_groq_key}
      />

      {/* Starter Onboarding Modal */}
      <OnboardingModal
        isOpen={isOnboardingOpen}
        onClose={handleCloseOnboarding}
        onLaunchDemo={() => setActiveTab(TABS.SINGLE)}
      />

      {/* Global Quick Command Palette (Ctrl+K / Cmd+K) */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
        onSelectTab={setActiveTab}
        onSelectTicker={(ticker) => {
          setActiveTab(TABS.SINGLE);
        }}
        onLaunchDemo={() => setActiveTab(TABS.SINGLE)}
        onOpenKeyModal={() => setIsKeyModalOpen(true)}
        onRebuildIndex={rebuildIndex}
        onOpenTour={() => setIsOnboardingOpen(true)}
      />

    </div>
  );
}
