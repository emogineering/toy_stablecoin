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
      console.log('통계 업데이트 실패:', err);
    }
  }, []);

  const fetchAllRequests = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:8000/admin/all-requests');
      const data = await res.json();
      setAllRequests(data);
      setLastUpdate(new Date());
    } catch (err) {
      console.log('신청 목록 업데이트 실패:', err);
    }
  }, []);

  const fetchTransfers = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:8000/admin/upbit-transfers');
      const data = await res.json();
      setTransfers(data);
    } catch (err) {
      console.log('입출금 내역 업데이트 실패:', err);
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
        setError('초기 데이터 로딩 실패');
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
    setApproveMsg('');
    try {
      const endpoint = type === 'burn' ? `approve-burn/${id}` : `approve/${id}`;
      const res = await fetch(`http://localhost:8000/admin/${endpoint}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '승인 실패');
      setApproveMsg(data.message);
      // 즉시 데이터 새로고침
      fetchAllRequests();
      fetchStats();
    } catch (err) {
      setApproveMsg(err.message);
    }
  };

  const handleReject = async (id) => {
    try {
      const res = await fetch(`http://localhost:8000/admin/reject-burn/${id}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '거절 실패');
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
      if (!res.ok) throw new Error(data.detail || '소각 신청 실패');
      setBurnMsg('소각 신청 완료!');
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
      if (!res.ok) throw new Error(data.detail || '동기화 실패');
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
    console.log('수동 새로고침 시작');
    try {
      // 로딩 상태 표시
      setLoading(true);
      
      // 모든 데이터를 병렬로 새로고침
      await Promise.all([
        fetchStats(),
        fetchAllRequests(),
        fetchTransfers()
      ]);
      
      console.log('수동 새로고침 완료');
    } catch (err) {
      console.error('수동 새로고침 실패:', err);
    } finally {
      setLoading(false);
    }
  };

  // 잔액 변화 표시 컴포넌트
  const BalanceChangeDisplay = () => {
    if (!balanceChange) {
      return <span style={{ color: '#666', fontSize: '0.9em' }}> (변화 없음)</span>;
    }
    
    const isPositive = balanceChange.amount > 0;
    const color = isPositive ? '#4CAF50' : '#f44336';
    const sign = isPositive ? '+' : '';
    
    return (
      <span style={{ color, fontSize: '0.9em', fontWeight: 'bold' }}>
        {' '}({sign}{balanceChange.amount.toFixed(6)} USDT)
        <span style={{ color: '#666', fontSize: '0.8em' }}>
          {' '}• {balanceChange.timestamp.toLocaleTimeString('ko-KR')}
        </span>
      </span>
    );
  };

  return (
    <div style={{ maxWidth: 1000, margin: '40px auto', padding: 20, border: '1px solid #ccc', borderRadius: 8 }}>
      <h2>관리자 대시보드</h2>
      
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
        <span>🔄 실시간 업데이트 활성화 (5초마다 자동 새로고침)</span>
        {lastUpdate && (
          <span style={{ color: '#666' }}>
            마지막 업데이트: {lastUpdate.toLocaleTimeString('ko-KR')}
          </span>
        )}
      </div>

      {stats && (
        <div style={{ marginBottom: 20, padding: 10, background: '#f8f8f8', borderRadius: 6 }}>
          <b>계좌 USDT 잔액:</b> {stats.usdt_balance !== undefined ? Number(stats.usdt_balance).toFixed(6) : '-'} USDT
          <BalanceChangeDisplay />
          <br/>
          <b>총 민팅된 USDG:</b> {stats.total_usdg_minted} USDG<br/>
          <b>총 소각된 USDG:</b> {stats.total_usdg_burned} USDG<br/>
          <b>현재 유통중인 USDG:</b> {stats.circulating_usdg !== undefined ? Number(stats.circulating_usdg).toFixed(6) : '-'} USDG
        </div>
      )}
      
      <h2>입출금 내역 (업비트)</h2>
      <div style={{ display: 'flex', gap: 10, marginBottom: 10, alignItems: 'center' }}>
        <button onClick={handleSyncUpbitTransfers}>업비트 전송 동기화</button>
        <button 
          onClick={handleManualRefresh} 
          disabled={loading}
          style={{ 
            background: loading ? '#ccc' : '#4CAF50', 
            color: 'white',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? '🔄 새로고침 중...' : '🔄 수동 새로고침'}
        </button>
      </div>
      {syncMsg && <div style={{ margin: '8px 0', color: syncMsg.includes('실패') ? 'red' : 'green' }}>{syncMsg}</div>}
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 30 }}>
        <thead>
          <tr>
            <th>구분</th><th>금액</th><th>통화</th><th>상태</th><th>트랜잭션ID</th><th>일시</th>
          </tr>
        </thead>
        <tbody>
          {transfers.map(tx => (
            <tr key={tx.id}>
              <td>{tx.type === 'deposit' ? '입금' : '출금'}</td>
              <td>{Number(tx.amount).toFixed(6)}</td>
              <td>{tx.currency}</td>
              <td>{tx.status}</td>
              <td style={{ fontSize: '0.9em' }}>{tx.tx_id}</td>
              <td>{tx.created_at ? new Date(new Date(tx.created_at).getTime() + 9 * 60 * 60 * 1000).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' }) : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>민팅/소각 신청 목록</h2>
      {loading ? <div>불러오는 중...</div> : error ? <div style={{ color: 'red' }}>{error}</div> : (
        <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 30 }}>
          <thead>
            <tr>
              <th>ID</th><th>타입</th><th>금액</th><th>지갑주소/메모</th><th>상태</th><th>신청일시</th><th>Action</th>
            </tr>
          </thead>
          <tbody>
            {allRequests.map(req => (
              <tr key={`${req.type}-${req.id}`}>
                <td>{req.id}</td>
                <td>
                  <span style={{ 
                    padding: '4px 8px', 
                    borderRadius: '4px', 
                    fontSize: '0.9em',
                    backgroundColor: req.type === 'mint' ? '#e3f2fd' : '#ffebee',
                    color: req.type === 'mint' ? '#1976d2' : '#d32f2f'
                  }}>
                    {req.type === 'mint' ? '민팅' : '소각'}
                  </span>
                </td>
                <td>{Number(req.amount).toFixed(6)}</td>
                <td style={{ fontSize: '0.9em' }}>
                  {req.type === 'mint' ? (req.eth_address || '-') : (req.tx_id || '-')}
                </td>
                <td>{req.status}</td>
                <td>{req.created_at ? new Date(new Date(req.created_at).getTime() + 9 * 60 * 60 * 1000).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' }) : '-'}</td>
                <td>
                  {req.status === 'pending' ? (
                    <>
                      <button onClick={() => handleApprove(req.id, req.type)}>승인</button>
                      {req.type === 'burn' && (
                        <button onClick={() => handleReject(req.id)} style={{ marginLeft: 8 }}>거절</button>
                      )}
                    </>
                  ) : req.status === 'approved' ? '승인됨' : '거절됨'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div style={{ margin: '30px 0', padding: 10, background: '#f3f3f3', borderRadius: 6 }}>
        <h3>임의 소각 신청</h3>
        <form onSubmit={handleManualBurn} style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <input type="number" min="0.000001" step="0.000001" placeholder="소각할 USDT 양" value={burnAmount} onChange={e => setBurnAmount(e.target.value)} required style={{ width: 120 }} />
          <input type="text" placeholder="메모(선택)" value={burnMemo} onChange={e => setBurnMemo(e.target.value)} style={{ width: 200 }} />
          <button type="submit">소각 신청</button>
        </form>
        {burnMsg && <div style={{ marginTop: 8, color: burnMsg.includes('완료') ? 'green' : 'red' }}>{burnMsg}</div>}
      </div>

      {approveMsg && <div style={{ marginTop: 20, color: approveMsg.includes('실패') ? 'red' : 'green' }}>{approveMsg}</div>}
    </div>
  );
}

export default AdminPage; 