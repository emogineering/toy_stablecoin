import React, { useEffect, useState, useRef } from 'react';

function classNames(...classes) {
  return classes.filter(Boolean).join(' ');
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [requests, setRequests] = useState([]);
  const [transfers, setTransfers] = useState([]);
  const [balanceChange, setBalanceChange] = useState(null);
  const prevBalance = useRef(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [syncMsg, setSyncMsg] = useState('');
  const [approveMsg, setApproveMsg] = useState('');
  const [burnModalOpen, setBurnModalOpen] = useState(false);
  const [burnAmount, setBurnAmount] = useState('');
  const [burnMemo, setBurnMemo] = useState('');
  const [burnMsg, setBurnMsg] = useState('');
  const [manualLoading, setManualLoading] = useState(false);
  const [manualMsg, setManualMsg] = useState('');

  // 데이터 fetch 함수
  const fetchData = () => {
    Promise.all([
      fetch('http://localhost:8000/admin/dashboard-stats').then(res => res.json()),
      fetch('http://localhost:8000/admin/all-requests').then(res => res.json()),
      fetch('http://localhost:8000/admin/upbit-transfers').then(res => res.json()),
    ])
      .then(([statsData, requestsData, transfersData]) => {
        // 잔액 변화량 계산
        if (prevBalance.current !== null && statsData.usdt_balance !== undefined) {
          const diff = statsData.usdt_balance - prevBalance.current;
          if (Math.abs(diff) > 0.000001) {
            setBalanceChange(diff);
          } else {
            setBalanceChange(0);
          }
        }
        prevBalance.current = statsData.usdt_balance;
        setStats(statsData);
        setRequests(requestsData);
        setTransfers(transfersData);
        setLastUpdate(new Date());
      })
      .catch(() => {
        // 에러 발생 시 조용히 처리 (사용자가 실시간 업데이트를 계속 볼 수 있도록)
      });
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  // Mint/Burn 승인/거절
  const handleApprove = async (id, type) => {
    setApproveMsg('');
    try {
      const endpoint = type === 'burn' ? `approve-burn/${id}` : `approve/${id}`;
      const res = await fetch(`http://localhost:8000/admin/${endpoint}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Approval failed');
      setApproveMsg(data.message);
      fetchData();
    } catch (err) {
      setApproveMsg(err.message);
    }
  };
  const handleReject = async (id, type) => {
    setApproveMsg('');
    try {
      const endpoint = type === 'burn' ? `reject-burn/${id}` : `reject/${id}`;
      const res = await fetch(`http://localhost:8000/admin/${endpoint}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Rejection failed');
      setApproveMsg(data.message);
      fetchData();
    } catch (err) {
      setApproveMsg(err.message);
    }
  };

  // Manual Burn
  const handleManualBurn = async (e) => {
    e.preventDefault();
    setBurnMsg('');
    setManualLoading(true);
    try {
      const res = await fetch('http://localhost:8000/admin/manual-burn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount: parseFloat(burnAmount), memo: burnMemo })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Burn request failed');
      setBurnMsg('Burn request completed!');
      setBurnAmount('');
      setBurnMemo('');
      setBurnModalOpen(false);
      fetchData();
    } catch (err) {
      setBurnMsg(err.message);
    } finally {
      setManualLoading(false);
    }
  };

  // Sync Upbit Transfers
  const handleSyncUpbitTransfers = async () => {
    setSyncMsg('');
    try {
      const res = await fetch('http://localhost:8000/admin/sync-upbit-transfers', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Sync failed');
      setSyncMsg(data.message);
      fetchData();
    } catch (err) {
      setSyncMsg(err.message);
    }
  };

  // Manual Refresh 개선
  const handleManualRefresh = async () => {
    setManualLoading(true);
    setManualMsg('');
    try {
      await fetchData();
      setManualMsg('수동 새로고침 완료!');
    } catch (e) {
      setManualMsg('새로고침 실패');
    } finally {
      setManualLoading(false);
    }
  };

  // 잔액 변화 표시
  const BalanceChangeDisplay = () => {
    if (!transfers || transfers.length === 0) return null;
    // 오늘 00:00~현재까지의 변화량 계산
    const now = new Date();
    const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    let todayChange = 0;
    transfers.forEach(t => {
      const tDate = new Date(t.created_at);
      if (tDate >= startOfDay) {
        if (t.type === 'deposit') todayChange += Number(t.amount);
        else if (t.type === 'withdraw') todayChange -= Number(t.amount);
      }
    });
    if (Math.abs(todayChange) < 0.000001) {
      return <span className="text-gray-400 text-sm"> (오늘 변화 없음)</span>;
    }
    const isPositive = todayChange > 0;
    return (
      <span className={classNames('text-sm font-bold', isPositive ? 'text-green-400' : 'text-red-400')}>
        {isPositive ? ` (오늘 총 +${todayChange.toFixed(6)}` : ` (오늘 총 ${todayChange.toFixed(6)}`} USDT)
      </span>
    );
  };

  return (
    <div className="min-h-screen bg-black text-white font-main">
      {/* 상단 네비게이션 */}
      <nav className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <div className="flex items-center gap-4">
          <span className="text-6xl font-futuristic tracking-widest text-neon-yellow" style={{fontSize: '3.5rem'}}>Dashboard</span>
        </div>
        <div className="flex gap-4">
          <button className="px-4 py-2 rounded-lg bg-neon-yellow text-black font-bold font-futuristic shadow hover:brightness-110 transition text-xl">Dashboard</button>
          <button className="px-4 py-2 rounded-lg bg-gray-800 text-neon-yellow font-futuristic border border-neon-yellow hover:bg-neon-yellow hover:text-black transition text-xl" onClick={() => setBurnModalOpen(true)}>Manual Burn</button>
          <button className="px-4 py-2 rounded-lg bg-neon-blue text-black font-bold font-futuristic shadow hover:brightness-110 transition text-xl" onClick={handleSyncUpbitTransfers}>Sync Upbit Transfers</button>
          <button className="px-4 py-2 rounded-lg bg-neon-green text-black font-bold font-futuristic shadow hover:brightness-110 transition text-xl" onClick={handleManualRefresh} disabled={manualLoading}>
            {manualLoading ? '로딩 중...' : 'Manual Refresh'}
          </button>
        </div>
      </nav>
      {manualMsg && (
        <div className="flex justify-end px-6 pt-2">
          <span className={classNames('text-lg', manualMsg.includes('완료') ? 'text-green-400' : 'text-red-400')}>{manualMsg}</span>
        </div>
      )}

      {/* 실시간 업데이트 안내 */}
      <div className="flex justify-between items-center bg-gray-800 text-neon-green px-6 py-3 text-xl">
        <span>🔄 Real-time updates active (auto-refresh every 5 seconds)</span>
        {lastUpdate && <span className="text-gray-300">Last update: {lastUpdate.toLocaleTimeString()}</span>}
      </div>

      {/* 상단 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 p-6">
        <div className="rounded-2xl bg-gray-900 p-6 shadow-lg flex flex-col items-start border-l-8 border-neon-yellow">
          <span className="font-futuristic text-3xl text-neon-yellow mb-2">Balance</span>
          <span className="text-6xl font-bold">{stats?.usdt_balance !== undefined ? Number(stats.usdt_balance).toLocaleString() : '-'} <span className="text-3xl font-normal">USDT</span></span>
          <BalanceChangeDisplay />
        </div>
        <div className="rounded-2xl bg-gray-900 p-6 shadow-lg flex flex-col items-start border-l-8 border-neon-green">
          <span className="font-futuristic text-3xl text-neon-green mb-2">Circulating Supply</span>
          <span className="text-6xl font-bold">{stats?.circulating_usdg !== undefined ? Number(stats.circulating_usdg).toLocaleString() : '-'} <span className="text-3xl font-normal">USDG</span></span>
        </div>
        <div className="rounded-2xl bg-gray-900 p-6 shadow-lg flex flex-col items-start border-l-8 border-neon-blue">
          <span className="font-futuristic text-3xl text-neon-blue mb-2">Minted / Burned</span>
          <span className="text-4xl font-bold">{stats?.total_usdg_minted !== undefined ? Number(stats.total_usdg_minted).toLocaleString() : '-'} / {stats?.total_usdg_burned !== undefined ? Number(stats.total_usdg_burned).toLocaleString() : '-'} <span className="text-3xl font-normal">USDG</span></span>
        </div>
      </div>

      {/* Mint/Burn Request List */}
      <div className="px-6 pb-6">
        <div className="flex justify-between items-center mb-4">
          <div className="font-futuristic text-3xl text-neon-yellow">Mint/Burn Requests</div>
        </div>
        {syncMsg && <div className={classNames('mb-2 text-xl', syncMsg.includes('failed') ? 'text-red-400' : 'text-green-400')}>{syncMsg}</div>}
        {approveMsg && <div className={classNames('mb-2 text-xl', approveMsg.includes('failed') ? 'text-red-400' : 'text-green-400')}>{approveMsg}</div>}
        <div className="overflow-x-auto bg-gray-900 rounded-2xl p-6 shadow-lg border border-gray-800">
          <table className="w-full text-xl">
            <thead>
              <tr className="text-gray-400">
                <th className="p-4">Type</th>
                <th className="p-4">Amount</th>
                <th className="p-4">Wallet</th>
                <th className="p-4">Memo</th>
                <th className="p-4">Status</th>
                <th className="p-4">Date</th>
                <th className="p-4">Action</th>
              </tr>
            </thead>
            <tbody>
              {requests.length === 0 ? (
                <tr><td colSpan={7} className="text-center text-gray-500 py-8 text-2xl">No requests</td></tr>
              ) : (
                requests.map((r) => (
                  <tr key={r.id} className="text-center border-b border-gray-800 last:border-0">
                    <td className="p-4">
                      <span className={
                        r.type === 'mint'
                          ? 'text-neon-blue font-futuristic'
                          : 'text-neon-green font-futuristic'
                      }>
                        {r.type === 'mint' ? 'Mint' : 'Burn'}
                      </span>
                    </td>
                    <td className="p-4">{Number(r.amount).toLocaleString()}</td>
                    <td className="p-4">{r.eth_address || '-'}</td>
                    <td className="p-4">{r.tx_id || '-'}</td>
                    <td className="p-4">
                      {r.status === 'pending' && <span className="text-yellow-400">Pending</span>}
                      {r.status === 'approved' && <span className="text-green-400">Approved</span>}
                      {r.status === 'rejected' && <span className="text-red-400">Rejected</span>}
                    </td>
                    <td className="p-4">{r.created_at ? new Date(r.created_at).toLocaleString() : '-'}</td>
                    <td className="p-4">
                      {r.status === 'pending' && (
                        <div className="flex flex-col gap-2">
                          <button className="px-4 py-2 rounded bg-neon-yellow text-black font-bold font-futuristic shadow hover:brightness-110 transition text-lg" onClick={() => handleApprove(r.id, r.type)}>Approve</button>
                          <button className="px-4 py-2 rounded bg-gray-800 text-neon-yellow font-futuristic border border-neon-yellow hover:bg-neon-yellow hover:text-black transition text-lg" onClick={() => handleReject(r.id, r.type)}>Reject</button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Transfer History */}
      <div className="px-6 pb-12">
        <div className="font-futuristic text-3xl text-neon-blue mb-4">Transfer History</div>
        <div className="overflow-x-auto bg-gray-900 rounded-2xl shadow-lg border border-gray-800">
          <table className="w-full text-xl">
            <thead>
              <tr className="text-gray-400">
                <th className="p-4">Type</th>
                <th className="p-4">Amount</th>
                <th className="p-4">Currency</th>
                <th className="p-4">Status</th>
                <th className="p-4">Transaction ID</th>
                <th className="p-4">Date</th>
              </tr>
            </thead>
            <tbody>
              {transfers.length === 0 ? (
                <tr><td colSpan={6} className="text-center text-gray-500 py-8 text-2xl">No transfers</td></tr>
              ) : (
                transfers.map(t => (
                  <tr key={t.id} className="text-center border-b border-gray-800 last:border-0">
                    <td className="p-4">{t.type === 'deposit' ? 'Deposit' : 'Withdrawal'}</td>
                    <td className="p-4">{Number(t.amount).toLocaleString()}</td>
                    <td className="p-4">{t.currency}</td>
                    <td className="p-4">{t.status}</td>
                    <td className="p-4">{t.tx_id}</td>
                    <td className="p-4">{t.created_at ? new Date(t.created_at).toLocaleString() : '-'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Manual Burn Modal */}
      {burnModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50">
          <div className="bg-gray-900 rounded-2xl p-8 shadow-2xl border-2 border-neon-yellow min-w-[500px] w-full max-w-xl">
            <div className="font-futuristic text-neon-yellow text-3xl mb-4">Manual Burn Request</div>
            <form onSubmit={handleManualBurn} className="flex flex-col gap-4">
              <input
                type="number"
                min="0.000001"
                step="0.000001"
                placeholder="USDT amount"
                value={burnAmount}
                onChange={e => setBurnAmount(e.target.value)}
                required
                className="rounded px-4 py-3 bg-black border border-neon-yellow text-neon-yellow focus:outline-none focus:ring-2 focus:ring-neon-yellow text-xl"
              />
              <input
                type="text"
                placeholder="Memo (optional)"
                value={burnMemo}
                onChange={e => setBurnMemo(e.target.value)}
                className="rounded px-4 py-3 bg-black border border-neon-yellow text-neon-yellow focus:outline-none focus:ring-2 focus:ring-neon-yellow text-xl"
              />
              <button
                type="submit"
                className="px-4 py-3 rounded bg-neon-yellow text-black font-bold font-futuristic shadow hover:brightness-110 transition text-xl"
                disabled={manualLoading}
              >
                {manualLoading ? 'Requesting...' : 'Request Burn'}
              </button>
              <button
                type="button"
                className="px-4 py-3 rounded bg-gray-800 text-neon-yellow font-futuristic border border-neon-yellow hover:bg-neon-yellow hover:text-black transition text-xl"
                onClick={() => setBurnModalOpen(false)}
              >
                Cancel
              </button>
              {burnMsg && <div className={classNames('text-center text-xl', burnMsg.includes('completed') ? 'text-green-400' : 'text-red-400')}>{burnMsg}</div>}
            </form>
          </div>
        </div>
      )}
    </div>
  );
} 