import React, { useEffect, useState, useCallback, useRef } from 'react';

function AdminPage() {
  const [allRequests, setAllRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [approveMsg, setApproveMsg] = useState('');
  const [stats, setStats] = useState(null);
  const [transfers, setTransfers] = useState([]);
  const [burnAmount, setBurnAmount] = useState('');
  const [burnMemo, setBurnMemo] = useState('');
  const [burnMsg, setBurnMsg] = useState('');
  const [syncMsg, setSyncMsg] = useState('');
  const [lastUpdate, setLastUpdate] = useState(null);
  const [balanceChange, setBalanceChange] = useState(null);
  const previousBalance = useRef(null);

  const fetchStats = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:8000/admin/dashboard-stats');
      const data = await res.json();
      
      // 잔액 변화 계산
      if (previousBalance.current !== null && data.usdt_balance !== undefined) {
        const change = data.usdt_balance - previousBalance.current;
        if (Math.abs(change) > 0.000001) { // 0.000001 USDT 이상 변화가 있을 때만 표시
          setBalanceChange({
            amount: change,
            timestamp: new Date()
          });
        } else {
          setBalanceChange(null);
        }
      }
      
      previousBalance.current = data.usdt_balance;
      setStats(data);
    } catch (err) {
      console.log('Statistics update failed:', err);
    }
  }, []);

  const fetchAllRequests = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:8000/admin/all-requests');
      const data = await res.json();
      setAllRequests(data);
      setLastUpdate(new Date());
    } catch (err) {
      console.log('Request list update failed:', err);
    }
  }, []);

  const fetchTransfers = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:8000/admin/upbit-transfers');
      const data = await res.json();
      setTransfers(data);
    } catch (err) {
      console.log('Transfer history update failed:', err);
    }
  }, []);

  // 초기 로딩
  useEffect(() => {
    setLoading(true);
    setError(null);
    
    const initialLoad = async () => {
      try {
        await Promise.all([
          fetchStats(),
          fetchAllRequests(),
          fetchTransfers()
        ]);
      } catch (err) {
        setError('Initial data loading failed');
      } finally {
        setLoading(false);
      }
    };
    
    initialLoad();
  }, [fetchStats, fetchAllRequests, fetchTransfers]);

  // 자동 새로고침 (5초마다)
  useEffect(() => {
    const interval = setInterval(() => {
      fetchStats();
      fetchAllRequests();
      fetchTransfers();
    }, 5000); // 5초마다 업데이트

    return () => clearInterval(interval);
  }, [fetchStats, fetchAllRequests, fetchTransfers]);

  const handleApprove = async (id, type) => {
    const confirmMessage = `Are you sure you want to approve this ${type} request?`;
    if (!window.confirm(confirmMessage)) {
      return;
    }
    
    setApproveMsg('');
    try {
      const endpoint = type === 'burn' ? `approve-burn/${id}` : `approve/${id}`;
      const res = await fetch(`http://localhost:8000/admin/${endpoint}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Approval failed');
      setApproveMsg(data.message);
      // 즉시 데이터 새로고침
      fetchAllRequests();
      fetchStats();
    } catch (err) {
      setApproveMsg(err.message);
    }
  };

  const handleReject = async (id, type) => {
    const confirmMessage = `Are you sure you want to reject this ${type} request? This action cannot be undone.`;
    if (!window.confirm(confirmMessage)) {
      return;
    }
    
    try {
      const endpoint = type === 'burn' ? `reject-burn/${id}` : `reject/${id}`;
      const res = await fetch(`http://localhost:8000/admin/${endpoint}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Rejection failed');
      // 즉시 데이터 새로고침
      fetchAllRequests();
      fetchStats();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleManualBurn = async (e) => {
    e.preventDefault();
    setBurnMsg('');
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
      // 즉시 데이터 새로고침
      fetchAllRequests();
    } catch (err) {
      setBurnMsg(err.message);
    }
  };

  const handleSyncUpbitTransfers = async () => {
    setSyncMsg('');
    try {
      const res = await fetch('http://localhost:8000/admin/sync-upbit-transfers', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Sync failed');
      setSyncMsg(data.message);
      // 즉시 데이터 새로고침
      fetchTransfers();
      fetchAllRequests();
      fetchStats();
    } catch (err) {
      setSyncMsg(err.message);
    }
  };

  const handleManualRefresh = async () => {
    console.log('Manual refresh started');
    try {
      // 로딩 상태 표시
      setLoading(true);
      
      // 모든 데이터를 병렬로 새로고침
      await Promise.all([
        fetchStats(),
        fetchAllRequests(),
        fetchTransfers()
      ]);
      
      console.log('Manual refresh completed');
    } catch (err) {
      console.error('Manual refresh failed:', err);
    } finally {
      setLoading(false);
    }
  };

  // 잔액 변화 표시 컴포넌트
  const BalanceChangeDisplay = () => {
    if (!balanceChange) {
      return <span style={{ color: '#666', fontSize: '0.9em' }}> (No change)</span>;
    }
    
    const isPositive = balanceChange.amount > 0;
    const color = isPositive ? '#4CAF50' : '#f44336';
    const sign = isPositive ? '+' : '';
    
    return (
      <span style={{ color, fontSize: '0.9em', fontWeight: 'bold' }}>
        {' '}({sign}{balanceChange.amount.toFixed(6)} USDT)
        <span style={{ color: '#666', fontSize: '0.8em' }}>
          {' '}• {balanceChange.timestamp.toLocaleTimeString('en-US')}
        </span>
      </span>
    );
  };

  return (
    <div style={{ maxWidth: 1000, margin: '40px auto', padding: 20, border: '1px solid #ccc', borderRadius: 8 }}>
      <h2>Admin Dashboard</h2>
      
      {/* 실시간 업데이트 상태 표시 */}
      <div style={{ 
        marginBottom: 10, 
        padding: '8px 12px', 
        background: '#e8f5e8', 
        borderRadius: 4, 
        fontSize: '0.9em',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <span>🔄 Real-time updates active (auto-refresh every 5 seconds)</span>
        {lastUpdate && (
          <span style={{ color: '#666' }}>
            Last update: {lastUpdate.toLocaleTimeString('en-US')}
          </span>
        )}
      </div>

      {stats && (
        <div style={{ marginBottom: 20, padding: 10, background: '#f8f8f8', borderRadius: 6 }}>
          <b>Account USDT Balance:</b> {stats.usdt_balance !== undefined ? Number(stats.usdt_balance).toFixed(6) : '-'} USDT
          <BalanceChangeDisplay />
          <br/>
          <b>Total USDG Minted:</b> {stats.total_usdg_minted} USDG<br/>
          <b>Total USDG Burned:</b> {stats.total_usdg_burned} USDG<br/>
          <b>Current Circulating USDG:</b> {stats.circulating_usdg !== undefined ? Number(stats.circulating_usdg).toFixed(6) : '-'} USDG
        </div>
      )}
      
      <h2>Transfer History (Upbit)</h2>
      <div style={{ display: 'flex', gap: 10, marginBottom: 10, alignItems: 'center' }}>
        <button onClick={handleSyncUpbitTransfers}>Sync Upbit Transfers</button>
        <button 
          onClick={handleManualRefresh} 
          disabled={loading}
          style={{ 
            background: loading ? '#ccc' : '#4CAF50', 
            color: 'white',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? '🔄 Refreshing...' : '🔄 Manual Refresh'}
        </button>
      </div>
      {syncMsg && <div style={{ margin: '8px 0', color: syncMsg.includes('failed') ? 'red' : 'green' }}>{syncMsg}</div>}
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 30 }}>
        <thead>
          <tr>
            <th>Type</th><th>Amount</th><th>Currency</th><th>Status</th><th>Transaction ID</th><th>Date</th>
          </tr>
        </thead>
        <tbody>
          {transfers.map(tx => (
            <tr key={tx.id}>
              <td>{tx.type === 'deposit' ? 'Deposit' : 'Withdrawal'}</td>
              <td>{Number(tx.amount).toFixed(6)}</td>
              <td>{tx.currency}</td>
              <td>{tx.status}</td>
              <td style={{ fontSize: '0.9em' }}>{tx.tx_id}</td>
              <td>{tx.created_at ? new Date(new Date(tx.created_at).getTime() + 9 * 60 * 60 * 1000).toLocaleString('en-US', { timeZone: 'Asia/Seoul' }) : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Mint/Burn Request List</h2>
      {loading ? <div>Loading...</div> : error ? <div style={{ color: 'red' }}>{error}</div> : (
        <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 30 }}>
          <thead>
            <tr>
              <th>No.</th><th>Type</th><th>Amount</th><th>Wallet</th><th>Memo</th><th>Status</th><th>Date</th><th>Action</th>
            </tr>
          </thead>
          <tbody>
            {allRequests.map((req, idx) => (
              <tr key={`${req.type}-${req.id}`}>
                <td>{idx + 1}</td>
                <td>{req.type === 'mint' ? 'Mint' : 'Burn'}</td>
                <td>{Number(req.amount).toFixed(6)}</td>
                <td>{req.type === 'mint' ? (req.eth_address || '-') : '-'}</td>
                <td>{req.tx_id || '-'}</td>
                <td>{req.status}</td>
                <td>{req.created_at ? new Date(new Date(req.created_at).getTime() + 9 * 60 * 60 * 1000).toLocaleString('en-US', { timeZone: 'Asia/Seoul' }) : '-'}</td>
                <td>
                  {req.status === 'pending' ? (
                    <>
                      <button onClick={() => handleApprove(req.id, req.type)}>Approve</button>
                      <button onClick={() => handleReject(req.id, req.type)} style={{ marginLeft: 8 }}>Reject</button>
                    </>
                  ) : req.status === 'approved' ? 'Approved' : 'Rejected'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div style={{ margin: '30px 0', padding: 10, background: '#f3f3f3', borderRadius: 6 }}>
        <h3>Manual Burn Request</h3>
        <form onSubmit={handleManualBurn} style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <input type="number" min="0.000001" step="0.000001" placeholder="USDT amount to burn" value={burnAmount} onChange={e => setBurnAmount(e.target.value)} required style={{ width: 120 }} />
          <input type="text" placeholder="Memo (optional)" value={burnMemo} onChange={e => setBurnMemo(e.target.value)} style={{ width: 200 }} />
          <button type="submit">Request Burn</button>
        </form>
        {burnMsg && <div style={{ marginTop: 8, color: burnMsg.includes('completed') ? 'green' : 'red' }}>{burnMsg}</div>}
      </div>

      {approveMsg && <div style={{ marginTop: 20, color: approveMsg.includes('failed') ? 'red' : 'green' }}>{approveMsg}</div>}
    </div>
  );
}

export default AdminPage; 