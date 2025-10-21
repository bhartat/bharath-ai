// frontend/src/app/dashboard/page.tsx (FINAL - Clean Slate)
'use client';
import { useEffect, useState, Suspense, useCallback, useRef } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { fetchApi } from '@/lib/api';
import { FiInbox, FiSend, FiFileText, FiLogOut, FiEdit, FiLoader, FiUser, FiX, FiPaperclip } from 'react-icons/fi';
import { FaMagic, FaRegPaperPlane } from 'react-icons/fa';
import Modal from 'react-modal';
import ReactMarkdown from 'react-markdown';

interface User { displayName: string; email: string; avatarUrl: string; }
interface Attachment { id: string; filename: string; mimeType: string; }
interface EmailHeader { id: string; subject: string; sender: string; snippet: string; }
interface EmailContent extends EmailHeader { body: string; attachments: Attachment[]; }

const customModalStyles = {
  content: { top: '50%', left: '50%', right: 'auto', bottom: 'auto', marginRight: '-50%', transform: 'translate(-50%, -50%)', backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '1rem', width: '90%', maxWidth: '600px', padding: '2rem' },
  overlay: { backgroundColor: 'rgba(0, 0, 0, 0.75)', zIndex: 50 },
};
if (typeof window !== 'undefined') { Modal.setAppElement('body'); }

const LoadingSpinner = () => <div className="flex items-center justify-center min-h-screen bg-gray-900"><FiLoader className="animate-spin text-blue-500 text-6xl" /></div>;

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
        console.error("Token verification failed.", error);
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

function DashboardUI() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [inbox, setInbox] = useState<EmailHeader[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<EmailContent | null>(null);
  const [aiResult, setAiResult] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState({ emails: true, emailContent: false, aiAction: false, sending: false });
  const [error, setError] = useState<string | null>(null);
  const [isReplyModalOpen, setIsReplyModalOpen] = useState(false);
  const [draftContent, setDraftContent] = useState('');

  const handleAuthSuccess = useCallback((userData: User) => {
    setUser(userData);
    fetchInbox();
  }, []);

  const fetchInbox = async () => {
    setIsLoading(prev => ({ ...prev, emails: true, emailContent: false, aiAction: false }));
    setSelectedEmail(null); setAiResult(null); setError(null);
    try {
      const data = await fetchApi('/gmail/inbox');
      setInbox(data.emails || []);
    } catch (err) { setError('Failed to fetch inbox.'); }
    finally { setIsLoading(prev => ({ ...prev, emails: false })); }
  };

  const handleSelectEmail = async (emailId: string) => {
    if (selectedEmail?.id === emailId) return;
    setSelectedEmail(null); setAiResult(null);
    setIsLoading(prev => ({ ...prev, emailContent: true }));
    try {
      const data = await fetchApi(`/gmail/email/${emailId}`);
      setSelectedEmail(data);
    } catch (err) { setError('Failed to fetch email content.'); }
    finally { setIsLoading(prev => ({ ...prev, emailContent: false })); }
  };
  
  const handleSummarizeEmail = async () => {
    if (!selectedEmail?.body) return;
    setAiResult(null); setIsLoading(prev => ({ ...prev, aiAction: true }));
    try {
      const data = await fetchApi('/ai/summarize', {
          method: 'POST', body: JSON.stringify({ text: selectedEmail.body })
      });
      setAiResult(data.summary);
    } catch (err) { setError('Failed to generate summary.'); setAiResult('Error: Failed to generate summary.'); }
    finally { setIsLoading(prev => ({ ...prev, aiAction: false })); }
  };

  const handleSummarizeAttachment = async (attachment: Attachment) => {
    if (!selectedEmail) return;
    setAiResult(null); setIsLoading(prev => ({ ...prev, aiAction: true }));
    try {
      const data = await fetchApi(`/gmail/email/${selectedEmail.id}/summarize-attachment`, {
        method: 'POST', body: JSON.stringify(attachment)
      });
      setAiResult(data.summary);
    } catch (err) { setError('Failed to summarize attachment.'); setAiResult('Error: Failed to summarize attachment.'); }
    finally { setIsLoading(prev => ({ ...prev, aiAction: false })); }
  };

  const handleOpenDraftReply = async () => {
    if (!selectedEmail) return;
    setIsReplyModalOpen(true); setDraftContent('🧠 Generating AI draft, please wait...'); setIsLoading(prev => ({ ...prev, aiAction: true }));
    try {
      const prompt = `Based on the following email, draft a professional reply.\n\n---EMAIL---\nSubject: ${selectedEmail.subject}\nFrom: ${selectedEmail.sender}\n\n${selectedEmail.body}\n\n---END EMAIL---`;
      const data = await fetchApi('/ai/generate-reply', { method: 'POST', body: JSON.stringify({ prompt }) });
      setDraftContent(data.reply);
    } catch (err) { setDraftContent('Error: Could not generate draft.'); }
    finally { setIsLoading(prev => ({ ...prev, aiAction: false })); }
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
        <div className="flex flex-col space-y-6">
          <button onClick={fetchInbox} className="p-3 bg-blue-600 rounded-lg text-white" title="Inbox"><FiInbox size={24} /></button>
          <button className="p-3 rounded-lg hover:bg-gray-700 text-gray-400" title="Sent"><FiSend size={24} /></button>
          <button className="p-3 rounded-lg hover:bg-gray-700 text-gray-400" title="Drafts"><FiFileText size={24} /></button>
        </div>
        <div className="mt-auto flex flex-col space-y-6">
          <button className="p-3 rounded-lg hover:bg-gray-700 text-gray-400" title="Profile"><FiUser size={24} /></button>
          <button onClick={handleLogout} className="p-3 rounded-lg hover:bg-red-500 text-gray-400 hover:text-white" title="Logout"><FiLogOut size={24} /></button>
        </div>
      </nav>

      <div className="w-[420px] border-r border-gray-700 overflow-y-auto flex-shrink-0">
        <div className="p-4 border-b border-gray-700 sticky top-0 bg-gray-900 z-10">
          <h2 className="text-2xl font-semibold">Inbox</h2>
          {isLoading.emails ? <span className="text-sm text-gray-400">Loading...</span> : <span className="text-sm text-gray-400">{inbox.length} messages</span>}
        </div>
        {isLoading.emails && <div className="flex justify-center p-8"><FiLoader className="animate-spin text-blue-500" /></div>}
        <div className="flex flex-col">
          {inbox.map((email) => (
            <div key={email.id} onClick={() => handleSelectEmail(email.id)} className={`p-4 border-b border-gray-700 cursor-pointer ${selectedEmail?.id === email.id ? 'bg-blue-900/50' : 'hover:bg-gray-800'}`}>
              <h3 className="text-sm font-bold truncate text-gray-100">{email.sender.replace(/<.*?>/g, '').trim()}</h3>
              <p className="text-sm font-medium truncate">{email.subject}</p>
              <p className="text-xs text-gray-400 truncate">{email.snippet}</p>
            </div>
          ))}
        </div>
      </div>

      <main className="flex-1 flex flex-col bg-gray-800/50">
        <div className="flex-1 p-2 overflow-y-auto">
          {isLoading.emailContent ? ( <div className="flex justify-center items-center h-full"><FiLoader className="animate-spin text-blue-500 text-4xl" /></div>
          ) : selectedEmail ? (
            <div className="bg-gray-900 rounded-lg h-full flex flex-col shadow-inner">
              <div className="p-4 border-b border-gray-700 flex-shrink-0">
                <h2 className="text-xl font-bold truncate">{selectedEmail.subject}</h2>
                <p className="text-sm text-gray-400 truncate">From: {selectedEmail.sender}</p>
                {selectedEmail.attachments && selectedEmail.attachments.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-gray-700">
                    <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Attachments</h3>
                    <div className="flex flex-col space-y-2">
                      {selectedEmail.attachments.map(att => (
                        <div key={att.id} className="bg-gray-800 p-2 rounded-md flex items-center justify-between">
                          <div className="flex items-center space-x-2 truncate"><FiPaperclip className="flex-shrink-0" /> <span className="text-sm">{att.filename || 'Attachment'}</span></div>
                          <button onClick={() => handleSummarizeAttachment(att)} className="px-2 py-1 text-xs bg-blue-600 rounded-md hover:bg-blue-700">Summarize</button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <iframe srcDoc={selectedEmail.body} title={selectedEmail.subject} className="w-full h-full border-none bg-white" sandbox="allow-same-origin" />
            </div>
          ) : ( <div className="h-full flex flex-col justify-center items-center text-gray-600"><FiEdit size={64} className="mb-4" /><p>Select an email to read it and use AI actions.</p></div> )}
        </div>
        
        {aiResult && (
            <div className="p-4 border-b border-t border-gray-700 bg-gray-800/50 max-h-48 overflow-y-auto flex-shrink-0">
                <h3 className="text-lg font-semibold mb-2 text-blue-400">AI Result</h3>
                <div className="prose prose-invert max-w-none text-sm"><ReactMarkdown>{aiResult}</ReactMarkdown></div>
            </div>
        )}
        
        <div className="p-4 border-t border-gray-700 bg-gray-900 flex space-x-2 flex-shrink-0">
          <button onClick={handleSummarizeEmail} className="px-4 py-2 bg-blue-600 rounded-lg flex items-center space-x-2 hover:bg-blue-700 disabled:opacity-50" disabled={!selectedEmail || isLoading.aiAction}>
            {isLoading.aiAction && !isReplyModalOpen ? <FiLoader className="animate-spin" /> : <FaMagic size={18} />}
            <span>Summarize Email</span>
          </button>
          <button onClick={handleOpenDraftReply} className="px-4 py-2 bg-gray-700 rounded-lg flex items-center space-x-2 hover:bg-gray-600 disabled:opacity-50" disabled={!selectedEmail}>
            <FiEdit size={18} />
            <span>Draft Reply</span>
          </button>
        </div>
      </main>

      <Modal isOpen={isReplyModalOpen} onRequestClose={() => setIsReplyModalOpen(false)} style={customModalStyles} contentLabel="Draft Reply Modal">
          <div className="text-white">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold">Draft Reply</h2>
              <button onClick={() => setIsReplyModalOpen(false)} className="hover:text-red-500"><FiX size={24} /></button>
            </div>
            {isLoading.aiAction ? (
                <div className="flex justify-center items-center h-64"><FiLoader className="animate-spin text-blue-500 text-3xl"/></div>
            ) : (
                <textarea 
                    value={draftContent}
                    onChange={(e) => setDraftContent(e.target.value)}
                    className="w-full h-64 p-2 bg-gray-800 border border-gray-600 rounded-md focus:ring-2 focus:ring-blue-500 focus:outline-none"
                />
            )}
            <div className="mt-6 flex justify-end space-x-4">
                <button onClick={() => setIsReplyModalOpen(false)} className="px-4 py-2 bg-gray-600 rounded-md hover:bg-gray-700">Close</button>
                <button onClick={handleSendReply} disabled={isLoading.sending || !draftContent} className="px-4 py-2 bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center">
                    {isLoading.sending && <FiLoader className="animate-spin mr-2" />}
                    <FaRegPaperPlane className="mr-2" />
                    Send Mail
                </button>
            </div>
          </div>
      </Modal>
    </div>
  );
}

export default function DashboardPageWrapper() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <DashboardUI />
    </Suspense>
  );
}