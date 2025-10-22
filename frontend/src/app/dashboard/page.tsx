// frontend/src/app/dashboard/page.tsx (FINAL - Definitive Version)
'use client';

import { useEffect, useState, Suspense, useCallback, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { fetchApi } from '@/lib/api';
import { FiInbox, FiSend, FiFileText, FiLogOut, FiEdit, FiLoader, FiUser, FiX, FiPaperclip, FiCheckSquare, FiCalendar, FiClock, FiRefreshCw } from 'react-icons/fi';
import { FaMagic, FaRegPaperPlane } from 'react-icons/fa';
import Modal from 'react-modal';
import ReactMarkdown from 'react-markdown';

// --- Types ---
interface User { displayName: string; email: string; avatarUrl: string; }
interface Attachment { id: string; filename: string; mimeType: string; }
interface EmailHeader { id: string; subject: string; sender: string; snippet: string; }
interface EmailContent extends EmailHeader { body: string; attachments: Attachment[]; }
interface AIAnalysis {
  summary: string;
  action_items: string[];
  key_dates: string[];
  error?: string;
}

// --- Modal Styling (Upgraded for Draft Reply) ---
const customModalStyles = {
  content: { top: '50%', left: '50%', right: 'auto', bottom: 'auto', marginRight: '-50%', transform: 'translate(-50%, -50%)', backgroundColor: '#111827', border: '1px solid #374151', borderRadius: '1rem', width: '90%', maxWidth: '700px', padding: '2rem', height: '80vh', display: 'flex', flexDirection: 'column' as const },
  overlay: { backgroundColor: 'rgba(0, 0, 0, 0.75)', zIndex: 50 },
};
if (typeof window !== 'undefined') Modal.setAppElement('body');

// --- Reusable Components ---
const LoadingSpinner = () => <div className="flex items-center justify-center min-h-screen bg-gray-900"><FiLoader className="animate-spin text-blue-500 text-6xl" /></div>;

// --- Auth Handler (Your original, working version) ---
function AuthHandler({ onAuthSuccess }: { onAuthSuccess: (user: User) => void }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const effectRan = useRef(false);
  useEffect(() => {
    if (effectRan.current) return;
    effectRan.current = true;
    const token = searchParams.get('token');
    const verifyToken = async (tokenToVerify: string) => {
      try {
        const userData = await fetchApi('/me', { headers: { 'Authorization': `Bearer ${tokenToVerify}` } });
        onAuthSuccess(userData);
      } catch (error) {
        localStorage.removeItem('authToken');
        router.push('/');
      }
    };
    if (token) {
      localStorage.setItem('authToken', token);
      router.replace('/dashboard', { scroll: false });
      verifyToken(token);
    } else {
      const storedToken = localStorage.getItem('authToken');
      if (storedToken) verifyToken(storedToken);
      else router.push('/');
    }
  }, [router, searchParams, onAuthSuccess]);
  return <LoadingSpinner />;
}

// --- Main Dashboard UI ---
function DashboardUI() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [inbox, setInbox] = useState<EmailHeader[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<EmailContent | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState({ emails: true, emailContent: false, aiAction: false, sending: false });
  const [isReplyModalOpen, setIsReplyModalOpen] = useState(false);
  const [draftContent, setDraftContent] = useState('');
  const lastDraftPrompt = useRef('');

  const handleAuthSuccess = useCallback((userData: User) => { setUser(userData); fetchInbox(); }, []);

  const fetchInbox = async () => {
    setIsLoading(prev => ({ ...prev, emails: true, emailContent: false, aiAction: false }));
    setSelectedEmail(null); setAiAnalysis(null);
    try {
      const data = await fetchApi('/gmail/inbox');
      setInbox(data.emails || []);
    } catch (err) { console.error(err); }
    finally { setIsLoading(prev => ({ ...prev, emails: false })); }
  };

  const handleSelectEmail = async (emailId: string) => {
    if (selectedEmail?.id === emailId) return;
    setSelectedEmail(null); setAiAnalysis(null);
    setIsLoading(prev => ({ ...prev, emailContent: true }));
    try {
      const data = await fetchApi(`/gmail/email/${emailId}`);
      setSelectedEmail(data);
    } catch (err) { console.error(err); }
    finally { setIsLoading(prev => ({ ...prev, emailContent: false })); }
  };
  
  const processAIResponse = (responseSummary: string) => {
    try {
       const parsed = JSON.parse(responseSummary);
       setAiAnalysis(parsed);
    } catch (e) {
       setAiAnalysis({ summary: responseSummary, action_items: [], key_dates: [] });
    }
  };

  const handleSummarizeEmail = async () => {
    if (!selectedEmail?.body) return;
    setAiAnalysis(null); setIsLoading(prev => ({ ...prev, aiAction: true }));
    try {
      const data = await fetchApi('/ai/summarize', { method: 'POST', body: JSON.stringify({ text: selectedEmail.body }) });
      processAIResponse(data.summary);
    } catch (err) { setAiAnalysis({ summary: "Failed to generate summary.", action_items:[], key_dates: [], error: "true" }); }
    finally { setIsLoading(prev => ({ ...prev, aiAction: false })); }
  };

  const handleSummarizeAttachment = async (attachment: Attachment) => {
    if (!selectedEmail) return;
    setAiAnalysis(null); setIsLoading(prev => ({ ...prev, aiAction: true }));
    try {
      const data = await fetchApi(`/gmail/email/${selectedEmail.id}/summarize-attachment`, { method: 'POST', body: JSON.stringify(attachment) });
      processAIResponse(data.summary);
    } catch (err) { setAiAnalysis({ summary: "Failed to summarize attachment.", action_items:[], key_dates: [], error: "true" }); }
    finally { setIsLoading(prev => ({ ...prev, aiAction: false })); }
  };

  const generateDraft = async (basePrompt: string) => {
    setDraftContent('🧠 Generating AI draft, please wait...');
    setIsLoading(prev => ({ ...prev, aiAction: true }));
    try {
      const data = await fetchApi('/ai/generate-reply', { method: 'POST', body: JSON.stringify({ prompt: basePrompt }) });
      setDraftContent(data.reply);
    } catch (err) {
      setDraftContent('Error: Could not generate draft.');
    } finally {
      setIsLoading(prev => ({ ...prev, aiAction: false }));
    }
  };

  const handleOpenDraftReply = () => {
    if (!selectedEmail) return;
    const prompt = `Based on the following email, draft a professional reply.\n\n---EMAIL---\nSubject: ${selectedEmail.subject}\nFrom: ${selectedEmail.sender}\n\n${selectedEmail.body}\n\n---END EMAIL---`;
    lastDraftPrompt.current = prompt;
    setIsReplyModalOpen(true);
    generateDraft(prompt);
  };
  
  const handleRegenerateDraft = () => {
    if (!lastDraftPrompt.current) return;
    const modifiedPrompt = `${lastDraftPrompt.current}\n\nPlease provide a different version of the reply with a slightly different tone.`;
    generateDraft(modifiedPrompt);
  };

  const handleSendReply = async () => {
    if (!selectedEmail || !draftContent) return;
    setIsLoading(prev => ({ ...prev, sending: true }));
    try {
        const recipient = selectedEmail.sender.match(/<(.+)>/)?.[1] || selectedEmail.sender;
        await fetchApi('/gmail/send', {
            method: 'POST',
            body: JSON.stringify({ to: recipient, subject: `Re: ${selectedEmail.subject}`, body: draftContent })
        });
        setIsReplyModalOpen(false);
    } catch (err) { alert('Failed to send email.'); }
    finally { setIsLoading(prev => ({ ...prev, sending: false })); }
  };

  const handleLogout = () => { localStorage.removeItem('authToken'); router.push('/'); };

  if (!user) return <AuthHandler onAuthSuccess={handleAuthSuccess} />;

  return (
    <div className="flex h-screen w-full bg-gray-900 text-gray-200 font-sans">
      <nav className="w-20 bg-gray-800 flex flex-col items-center py-6 space-y-8 flex-shrink-0">
        <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center text-white text-2xl font-bold">B</div>
        <div className="flex flex-col space-y-6"><button onClick={fetchInbox} className="p-3 bg-blue-600 rounded-lg text-white" title="Inbox"><FiInbox size={24} /></button></div>
        <div className="mt-auto flex flex-col space-y-6"><button onClick={handleLogout} className="p-3 rounded-lg hover:bg-red-500 text-gray-400 hover:text-white" title="Logout"><FiLogOut size={24} /></button></div>
      </nav>

      <div className="w-[420px] border-r border-gray-700 overflow-y-auto flex-shrink-0">
        <div className="p-4 border-b border-gray-700 sticky top-0 bg-gray-900 z-10"><h2 className="text-2xl font-semibold">Inbox</h2></div>
        {inbox.map((email) => (<div key={email.id} onClick={() => handleSelectEmail(email.id)} className={`p-4 border-b border-gray-700 cursor-pointer ${selectedEmail?.id === email.id ? 'bg-blue-900/50' : 'hover:bg-gray-800'}`}><h3 className="text-sm font-bold truncate text-gray-100">{email.sender.replace(/<.*?>/g, '').trim()}</h3><p className="text-sm font-medium truncate">{email.subject}</p></div>))}
      </div>
      
      <main className="flex-1 flex flex-col bg-gray-800/50">
        <div className="flex-1 p-4 overflow-y-auto flex gap-4">
            <div className={`${aiAnalysis ? 'w-1/2' : 'w-full'} transition-all duration-300 flex flex-col`}>
                {selectedEmail ? (
                    <div className="bg-gray-900 rounded-lg h-full flex flex-col shadow-inner border border-gray-700 overflow-hidden">
                        <div className="p-4 border-b border-gray-700 bg-gray-800/50">
                            <h2 className="text-xl font-bold truncate">{selectedEmail.subject}</h2><p className="text-sm text-gray-400">From: {selectedEmail.sender}</p>
                             {selectedEmail.attachments && selectedEmail.attachments.length > 0 && (
                                <div className="mt-3 flex flex-wrap gap-2">
                                    {selectedEmail.attachments.map(att => (<div key={att.id} className="bg-slate-700 pl-2 pr-1 py-1 rounded-full flex items-center text-xs"><FiPaperclip className="mr-1"/> <span className="truncate max-w-[150px]">{att.filename}</span><button onClick={() => handleSummarizeAttachment(att)} className="ml-2 p-1 bg-blue-600 rounded-full hover:bg-blue-500" title="Summarize Attachment"><FaMagic size={10}/></button></div>))}
                                </div>
                            )}
                        </div>
                        <iframe srcDoc={selectedEmail.body} className="w-full flex-1 bg-white" sandbox="allow-same-origin" />
                    </div>
                ) : ( <div className="h-full flex items-center justify-center text-gray-500">Select an email</div> )}
            </div>

            {isLoading.aiAction && !aiAnalysis && <div className="w-1/2 flex items-center justify-center"><FiLoader className="animate-spin text-blue-500 text-4xl" /></div>}
            
            {aiAnalysis && (
                <div className="w-1/2 bg-slate-900 rounded-lg border border-blue-900/50 shadow-xl overflow-y-auto p-6 space-y-6 animate-in slide-in-from-right-10">
                    <div className="flex items-center justify-between"><h3 className="text-xl font-bold text-blue-400 flex items-center"><FaMagic className="mr-2"/> Intelligence Report</h3></div>
                    <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700"><h4 className="text-sm font-semibold text-gray-400 uppercase mb-2">Summary</h4><p className="text-gray-200 leading-relaxed">{aiAnalysis.summary}</p></div>
                    {aiAnalysis.action_items && aiAnalysis.action_items.length > 0 && (<div><h4 className="text-sm font-semibold text-green-400 uppercase mb-3 flex items-center"><FiCheckSquare className="mr-2"/> Action Items</h4><ul className="space-y-2">{aiAnalysis.action_items.map((item, i) => (<li key={i} className="flex items-start bg-slate-800/30 p-3 rounded-md border border-slate-700/50"><input type="checkbox" className="mt-1 mr-3 accent-green-500" /><span className="text-gray-300">{item}</span></li>))}</ul></div>)}
                    {aiAnalysis.key_dates && aiAnalysis.key_dates.length > 0 && (<div><h4 className="text-sm font-semibold text-yellow-400 uppercase mb-3 flex items-center"><FiCalendar className="mr-2"/> Key Dates</h4><ul className="space-y-2">{aiAnalysis.key_dates.map((date, i) => (<li key={i} className="flex items-center bg-slate-800/30 p-3 rounded-md border border-slate-700/50 text-gray-300"><FiClock className="mr-3 text-yellow-500/50"/> {date}</li>))}</ul></div>)}
                </div>
            )}
        </div>

        <div className="p-4 bg-gray-900 border-t border-gray-800 flex gap-3">
             <button onClick={handleSummarizeEmail} disabled={!selectedEmail || isLoading.aiAction} className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium flex items-center gap-2 disabled:opacity-50 transition-colors">{isLoading.aiAction ? <FiLoader className="animate-spin"/> : <FaMagic/>} Summarize</button>
             <button onClick={handleOpenDraftReply} disabled={!selectedEmail} className="px-6 py-3 bg-slate-700 hover:bg-slate-600 rounded-lg font-medium flex items-center gap-2 transition-colors"><FiEdit/> Draft Reply</button>
        </div>
      </main>

      <Modal isOpen={isReplyModalOpen} onRequestClose={() => setIsReplyModalOpen(false)} style={customModalStyles}>
         <div className="h-full flex flex-col">
            <div className="flex justify-between items-center mb-4 flex-shrink-0">
              <h2 className="text-2xl font-bold text-white">Draft Reply</h2>
              <button onClick={() => setIsReplyModalOpen(false)} className="text-gray-400 hover:text-white"><FiX size={24}/></button>
            </div>
            <textarea value={draftContent} onChange={e => setDraftContent(e.target.value)} className="flex-1 bg-slate-800 border border-slate-600 rounded-lg p-4 text-white resize-none focus:ring-2 focus:ring-blue-500 outline-none" />
            <div className="mt-4 flex justify-between items-center flex-shrink-0">
                <button onClick={handleRegenerateDraft} disabled={isLoading.aiAction} className="px-4 py-2 bg-gray-600 rounded-md hover:bg-gray-700 text-sm flex items-center gap-2 disabled:opacity-50">
                    {isLoading.aiAction ? <FiLoader className="animate-spin" /> : <FiRefreshCw />}
                    Regenerate
                </button>
                <div className="flex gap-3">
                    <button onClick={() => setIsReplyModalOpen(false)} className="px-6 py-3 bg-slate-700 rounded-lg hover:bg-slate-600 font-medium">Close</button>
                    <button onClick={handleSendReply} disabled={isLoading.sending || isLoading.aiAction} className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-medium flex items-center gap-2 disabled:opacity-50">
                        {isLoading.sending ? <FiLoader className="animate-spin"/> : <FaRegPaperPlane/>} Send
                    </button>
                </div>
            </div>
         </div>
      </Modal>
    </div>
  );
}

export default function DashboardPageWrapper() { return <Suspense fallback={<LoadingSpinner />}><DashboardUI /></Suspense>; }