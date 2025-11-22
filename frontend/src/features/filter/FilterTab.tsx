import React, { useState, useRef } from 'react';
import { useSettings, useUpdateSettings } from '../../hooks/useYoutubeQuery';

// ----------------------------------------------------------------------
// [내부 컴포넌트] 필터 섹션 (화이트리스트/블랙리스트 공통 UI)
// ----------------------------------------------------------------------
interface FilterSectionProps {
  title: string;
  description: string;
  tags: string[];
  onUpdateTags: (newTags: string[]) => void;
  placeholder?: string;
}

const FilterSection = ({ title, description, tags, onUpdateTags, placeholder }: FilterSectionProps) => {
  const [input, setInput] = useState('');
  const [showHelp, setShowHelp] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // 태그 추가 로직 (엔터 또는 쉼표)
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addTag();
    }
  };

  const addTag = () => {
    const trimmed = input.trim().replace(/,/g, ''); // 쉼표 제거
    if (trimmed && !tags.includes(trimmed)) {
      const newTags = [...tags, trimmed];
      onUpdateTags(newTags);
      setInput('');
    }
  };

  // 태그 삭제
  const removeTag = (tagToRemove: string) => {
    const newTags = tags.filter(tag => tag !== tagToRemove);
    onUpdateTags(newTags); 
  };

  // 전체 삭제
  const clearAll = () => {
    onUpdateTags([]);
    setInput('');
    inputRef.current?.focus();
  };

  // 컨테이너 클릭 시 인풋에 포커스
  const handleContainerClick = () => {
    inputRef.current?.focus();
  };

  return (
    <section className="mb-8">
      {/* 헤더 및 도움말 아이콘 */}
      <div className="flex items-center mb-3 relative">
        <h3 className="font-bold text-lg text-black mr-2">{title}</h3>
        <button 
          onClick={() => setShowHelp(!showHelp)}
          className="text-black hover:text-gray-600 transition-colors focus:outline-none"
        >
          {/* 물음표 아이콘 */}
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
        </button>

        {/* 툴팁 (도움말) */}
        {showHelp && (
          <div className="absolute left-0 top-8 z-10 w-full max-w-md bg-white border border-gray-200 p-4 rounded-xl shadow-lg text-sm text-gray-700 leading-relaxed animate-fade-in-down">
            {description}
          </div>
        )}
      </div>

      {/* 입력 컨테이너 */}
      <div 
        onClick={handleContainerClick}
        className="border-2 border-black rounded-2xl p-4 min-h-[80px] flex items-start bg-white cursor-text relative"
      >
        <div className="flex flex-wrap gap-2 flex-1 pr-10">
          {/* 태그 리스트 */}
          {tags.map((tag) => (
            <span 
              key={tag} 
              className="inline-flex items-center px-4 py-1.5 rounded-full bg-gray-200 text-gray-800 text-base font-medium"
            >
              {tag}
              <button 
                onClick={(e) => {
                  e.stopPropagation(); 
                  removeTag(tag);
                }}
                className="ml-2 text-gray-500 hover:text-black font-bold"
              >
                ✕
              </button>
            </span>
          ))}

          {/* 실제 Input 필드 */}
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={addTag} // 포커스 잃을 때도 추가
            placeholder={tags.length === 0 ? placeholder : ''}
            className="flex-grow min-w-[120px] bg-transparent outline-none text-gray-800 placeholder-gray-400 py-1.5"
          />
        </div>

        {/* 전체 삭제 버튼 */}
        {tags.length > 0 && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              clearAll();
            }}
            className="absolute right-4 top-1/2 -translate-y-1/2 p-2 text-black hover:text-gray-600"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        )}
      </div>
    </section>
  );
};

// ----------------------------------------------------------------------
// [메인] 필터 탭
// ----------------------------------------------------------------------
const FilterTab = () => {
  // 상태 관리
  // 1. Chrome Storage에서 설정 불러오기
  const { data: settings } = useSettings();
  
  // 2. 설정 저장(Mutation) 훅 가져오기
  const updateSettingsMutation = useUpdateSettings();

  // 데이터 로딩 중이면 아무것도 안 보여주거나 로딩 스피너
  if (!settings) return null;

  // 화이트리스트 업데이트 함수
  const handleUpdateWhiteList = (newTags: string[]) => {
    updateSettingsMutation.mutate({
      ...settings,
      whiteList: newTags // 기존 설정 유지하고 whiteList만 변경
    });
  };

  // 블랙리스트 업데이트 함수
  const handleUpdateBlackList = (newTags: string[]) => {
    updateSettingsMutation.mutate({
      ...settings,
      blackList: newTags // 기존 설정 유지하고 blackList만 변경
    });
  };

  return (
    <div className="p-6 bg-white h-full">
      {/* 1. 화이트리스트 섹션 */}
      <FilterSection
        title="화이트리스트"
        description="이 목록에 등록된 단어는 필터링 시스템에서 항상 안전한 단어로 인식됩니다. 욕설로 오해받을 수 있는 채널 밈, 애칭 등을 등록하여 오탐을 방지할 수 있습니다."
        tags={settings.whiteList || []} 
        onUpdateTags={handleUpdateWhiteList}
        placeholder="단어 입력 후 엔터 또는 쉼표"
      />

      {/* 2. 블랙리스트 섹션 */}
      <FilterSection
        title="블랙리스트"
        description="이 목록의 단어가 포함된 댓글은 필터링 강도와 관계없이 시스템이 가장 먼저, 그리고 확실하게 차단/숨김 조치를 취합니다."
        tags={settings.blackList || []}
        onUpdateTags={handleUpdateBlackList}
        placeholder="단어 입력 후 엔터 또는 쉼표"
      />
    </div>
  );
};

export default FilterTab;