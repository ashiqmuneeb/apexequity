import React, { useState } from 'react';
import Header from './components/common/Header';
import Footer from './components/layout/Footer';
import ApiKeyModal from './components/common/ApiKeyModal';
import FinancialBackground from './components/common/FinancialBackground';
import StatusBanner from './components/common/StatusBanner';
import TabNavigation from './components/layout/TabNavigation';
import OnboardingModal from './components/common/OnboardingModal';
import CommandPalette from './components/common/CommandPalette';
import SingleStockView from './features/singleStock/SingleStockView';
import ComparisonView from './features/comparison/ComparisonView';
import CustomQueryView from './features/customQuery/CustomQueryView';
import ArticleManager from './features/articles/ArticleManager';
import { useSystemStatus } from './hooks/useSystemStatus';
import { TABS } from './constants/stockTickers';

export default function App() {
  const [activeTab, setActiveTab] = useState(TABS.SINGLE);
  const [selectedTicker, setSelectedTicker] = useState('NVDA');
  const [customInitialPrompt, setCustomInitialPrompt] = useState('');
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  const {
    status,
    isKeyModalOpen,
    setIsKeyModalOpen,
    isRebuilding,
    rebuildFeedback,
    fetchStatus,
    rebuildIndex,
  } = useSystemStatus();

  const handleNavigateCustom = (presetPrompt) => {
    setCustomInitialPrompt(presetPrompt);
    setActiveTab(TABS.CUSTOM);
  };

  const handleCloseOnboarding = () => {
    setIsOnboardingOpen(false);
    localStorage.setItem('apexequity_tour_dismissed', 'true');
  };

  const handleSelectTicker = (ticker) => {
    setSelectedTicker(ticker);
    setActiveTab(TABS.SINGLE);
  };

  return (
    <div className="finance-bg relative min-h-screen bg-[#f8fafc] text-slate-800 flex flex-col font-sans overflow-x-hidden">
      
      {/* Dynamic Ambient Financial Chart & Glow Waves */}
      <FinancialBackground />

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

      {/* Floating Rebuild Alert with accessible contrast */}
      {rebuildFeedback && (
        <div
          className={`relative z-20 py-2.5 px-4 text-center text-xs font-semibold ${
            rebuildFeedback.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border-b border-emerald-200'
              : 'bg-rose-50 text-rose-800 border-b border-rose-200'
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
          articleCount={status?.indexed_articles_count ?? 0}
        />

        {/* Tab Views */}
        <div>
          {activeTab === TABS.SINGLE && (
            <SingleStockView
              availableTickers={status?.articles}
              selectedTicker={selectedTicker}
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
              initialPrompt={customInitialPrompt}
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

      {/* Institutional Legal & Technical Footer */}
      <Footer />

      {/* Global Modals */}
      <ApiKeyModal
        isOpen={isKeyModalOpen}
        onClose={() => setIsKeyModalOpen(false)}
        currentHasKey={status?.has_groq_key}
      />

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
        onSelectTicker={handleSelectTicker}
        onLaunchDemo={() => setActiveTab(TABS.SINGLE)}
        onOpenKeyModal={() => setIsKeyModalOpen(true)}
        onRebuildIndex={rebuildIndex}
        onOpenTour={() => setIsOnboardingOpen(true)}
      />

    </div>
  );
}
