import { useState, useEffect } from 'react'
import axios from 'axios'
import { 
  LayoutDashboard, 
  Users, 
  CreditCard, 
  History, 
  Plus, 
  Search,
  MoreVertical,
  TrendingUp,
  UserCheck,
  LogOut,
  UserMinus,
  DoorOpen,
  Calendar as CalendarIcon,
  X,
  Wallet,
  AlertCircle,
  Clock,
  CheckCircle2,
  Receipt,
  Wrench,
  ShieldCheck,
  MessageSquare,
  Share2,
  FileText,
  AlertTriangle,
  StickyNote,
  Edit2,
  Trash2,
  Download,
  Menu
} from 'lucide-react'
import DatePicker from "react-datepicker"
import "react-datepicker/dist/react-datepicker.css"
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

const MONTHS = [
  "January", "February", "March", "April", "May", "June", 
  "July", "August", "September", "October", "November", "December"
]

const YEARS = [2022, 2023, 2024, 2025, 2026]

function App() {
  const [loading, setLoading] = useState(false)
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [tenants, setTenants] = useState([])
  const [newTenant, setNewTenant] = useState({ 
    name: '', 
    phone: '', 
    room_number: '', 
    rent_amount: '', 
    aadhar_number: '',
    emergency_contact: '',
    move_in_date: new Date(),
    status: 'active'
  })
  const [selectedTenant, setSelectedTenant] = useState(null)
  const [view, setView] = useState('dashboard') 
  const [filterStatus, setFilterStatus] = useState('All')
  const [minRent, setMinRent] = useState('')
  const [maxRent, setMaxRent] = useState('')
  const [notes, setNotes] = useState([])
  const [noteData, setNoteData] = useState({ title: '', content: '', category: 'General' })
  const [showNoteModal, setShowNoteModal] = useState(false)
  const [editingNote, setEditingNote] = useState(null)
  const [activeNoteCategory, setActiveNoteCategory] = useState('All')
  const [searchQuery, setSearchQuery] = useState('')
  const [paymentHistory, setPaymentHistory] = useState([])
  const [expenses, setExpenses] = useState([])
  const [maintenance, setMaintenance] = useState([])
  const [showAddForm, setShowAddForm] = useState(false)
  const [showPayModal, setShowPayModal] = useState(false)
  const [showLeavingModal, setShowLeavingModal] = useState(false)
  const [showExpenseModal, setShowExpenseModal] = useState(false)
  const [editingExpense, setEditingExpense] = useState(null)
  const [showMaintenanceModal, setShowMaintenanceModal] = useState(false)
  const [editingMaintenance, setEditingMaintenance] = useState(null)
  const [showDocumentModal, setShowDocumentModal] = useState(false)
  const [tenantDocuments, setTenantDocuments] = useState([])
  const [documentData, setDocumentData] = useState({
    name: '',
    type: 'Aadhar',
    file: null
  })
  const [leavingDate, setLeavingDate] = useState(new Date())
  const [expenseData, setExpenseData] = useState({
    title: '',
    amount: '',
    category: 'Repair',
    date: new Date(),
    description: ''
  })
  const [maintenanceData, setMaintenanceData] = useState({
    tenant_id: '',
    tenant_name: '',
    issue: '',
    notes: '',
    priority: 'Medium',
    status: 'pending',
    cost: '',
    created_at: new Date()
  })
  const [paymentData, setPaymentData] = useState({ 
    amount: '', 
    pending_amount: '',
    initial_reading: '',
    current_reading: '',
    rate_per_unit: '8', // Default rate
    electricity_amount: 0,
    date: new Date(),
    month: MONTHS[new Date().getMonth()],
    year: new Date().getFullYear(),
    method: 'Cash',
    status: 'paid'
  })
  const [loginData, setLoginData] = useState({ username: '', password: '' })
  const [loginError, setLoginError] = useState('')

  useEffect(() => {
    if (token) {
      fetchTenants()
      fetchExpenses()
      fetchMaintenance()
      fetchNotes()
    }
  }, [token, filterStatus, minRent, maxRent, searchQuery])

  const fetchNotes = async () => {
    try {
      const response = await apiRequest('get', '/notes')
      setNotes(response.data)
    } catch (error) {
      console.error('Error fetching notes:', error)
    }
  }

  const fetchExpenses = async () => {
    try {
      const response = await apiRequest('get', '/expenses')
      setExpenses(response.data)
    } catch (error) {
      console.error('Error fetching expenses:', error)
    }
  }

  const fetchMaintenance = async () => {
    try {
      const response = await apiRequest('get', '/maintenance')
      setMaintenance(response.data)
    } catch (error) {
      console.error('Error fetching maintenance:', error)
    }
  }

  const openDocumentModal = async (tenant) => {
    setSelectedTenant(tenant)
    setShowDocumentModal(true)
    try {
      const response = await apiRequest('get', `/documents/${tenant._id}`)
      setTenantDocuments(response.data)
    } catch (error) {
      console.error('Error fetching documents:', error)
    }
  }

  const handleUploadDocument = async (e) => {
    e.preventDefault()
    if (!documentData.file) return alert("Please select a file")
    
    const formData = new FormData()
    formData.append('file', documentData.file)
    formData.append('name', documentData.name)
    formData.append('doc_type', documentData.type)

    try {
      await axios.post(`${API_BASE}/document/upload/${selectedTenant._id}`, formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        }
      })
      alert("Document uploaded successfully!")
      setDocumentData({ name: '', type: 'Aadhar', file: null })
      // Refresh documents
      const response = await apiRequest('get', `/documents/${selectedTenant._id}`)
      setTenantDocuments(response.data)
      fetchTenants()
    } catch (error) {
      console.error('Error uploading document:', error)
      const detail = error.response?.data?.detail || "Error uploading document"
      alert(detail)
    }
  }

  const handleDeleteDocument = async (docId) => {
    if (!window.confirm("Are you sure you want to delete this document?")) return
    try {
      await apiRequest('delete', `/document/${docId}`)
      setTenantDocuments(prev => prev.filter(d => d._id !== docId))
      fetchTenants()
    } catch (error) {
      console.error('Error deleting document:', error)
    }
  }

  const apiRequest = async (method, url, data = null) => {
    setLoading(true)
    try {
      const config = {
        method,
        url: `${API_BASE}${url}`,
        headers: { Authorization: `Bearer ${token}` },
        data
      }
      return await axios(config)
    } catch (error) {
      if (error.response?.status === 401) {
        handleLogout()
      }
      throw error
    } finally {
      setLoading(false)
    }
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoginError('')
    try {
      const params = new URLSearchParams()
      params.append('username', loginData.username)
      params.append('password', loginData.password)
      
      const response = await axios.post(`${API_BASE}/token`, params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      const { access_token } = response.data
      localStorage.setItem('token', access_token)
      setToken(access_token)
    } catch (error) {
      if (error.response?.status === 401) {
        setLoginError('Invalid username or password')
      } else if (error.response?.status === 500) {
        const detail = error.response.data?.detail || 'Server Error'
        const errMsg = error.response.data?.error_message ? ` - ${error.response.data.error_message}` : ''
        setLoginError(`${detail}${errMsg}`)
        console.error('Full Error:', error.response.data)
      } else {
        setLoginError('Connection Error: Is the backend running?')
      }
    }
  }

  const handleLogout = () => {
    if (window.confirm("Are you sure you want to sign out?")) {
      localStorage.removeItem('token')
      setToken(null)
      setTenants([])
    }
  }

  const fetchTenants = async () => {
    try {
      const params = new URLSearchParams()
      if (filterStatus !== 'All') params.append('status', filterStatus)
      if (minRent) params.append('min_rent', minRent)
      if (maxRent) params.append('max_rent', maxRent)
      if (searchQuery) params.append('search', searchQuery)

      const response = await apiRequest('get', `/tenants?${params.toString()}`)
      setTenants(response.data)
    } catch (error) {
      console.error('Error fetching rental persons:', error)
      alert(`Error fetching rental persons: ${error.response?.data?.detail || error.message}`)
    }
  }

  const handleAddTenant = async (e) => {
    e.preventDefault()
    try {
      const data = {
        ...newTenant,
        rent_amount: parseFloat(newTenant.rent_amount || 0),
        move_in_date: newTenant.move_in_date instanceof Date 
          ? newTenant.move_in_date.toISOString().split('T')[0] 
          : new Date().toISOString().split('T')[0],
        aadhar_number: (newTenant.aadhar_number || '').trim() || null,
        emergency_contact: (newTenant.emergency_contact || '').trim() || null
      }
      await apiRequest('post', '/tenant', data)
      setNewTenant({ 
        name: '', 
        phone: '', 
        room_number: '', 
        rent_amount: '', 
        aadhar_number: '',
        emergency_contact: '',
        move_in_date: new Date(),
        status: 'active'
      })
      setShowAddForm(false)
      fetchTenants()
    } catch (error) {
      console.error('Error adding rental person:', error)
      let errMsg = 'Error adding rental person. Please check all details.'
      if (error.response?.data?.detail) {
        if (typeof error.response.data.detail === 'string') {
          errMsg = error.response.data.detail
        } else if (Array.isArray(error.response.data.detail)) {
          errMsg = error.response.data.detail.map(e => `${e.loc.join('.')}: ${e.msg}`).join('\n')
        }
      }
      alert(errMsg)
    }
  }

  const openLeavingModal = (tenant) => {
    setSelectedTenant(tenant)
    setLeavingDate(new Date())
    setShowLeavingModal(true)
  }

  const handleConfirmLeaving = async (e) => {
    e.preventDefault()
    try {
      await apiRequest('patch', `/tenant/${selectedTenant._id}`, { 
        status: 'leaving', 
        move_out_date: leavingDate.toISOString().split('T')[0]
      })
      setShowLeavingModal(false)
      fetchTenants()
    } catch (error) {
      console.error('Error updating status:', error)
    }
  }

  const handleMarkActive = async (tenantId) => {
    try {
      await apiRequest('patch', `/tenant/${tenantId}`, { status: 'active', move_out_date: null })
      fetchTenants()
    } catch (error) {
      console.error('Error updating status:', error)
    }
  }

  const openPayModal = (tenant) => {
    setSelectedTenant(tenant)
    // Find last payment to get initial reading
    const lastPayment = tenant.payments?.length > 0 
      ? [...tenant.payments].sort((a,b) => new Date(b.date) - new Date(a.date))[0]
      : null;

    setPaymentData({ 
      amount: tenant.rent_amount || '', 
      pending_amount: '',
      initial_reading: lastPayment?.current_reading || '',
      current_reading: '',
      rate_per_unit: '8', // You can make this configurable
      electricity_amount: 0,
      date: new Date(),
      month: MONTHS[new Date().getMonth()],
      year: new Date().getFullYear(),
      method: 'Cash',
      status: 'paid'
    })
    setShowPayModal(true)
  }

  const handleRecordPayment = async (e) => {
    e.preventDefault()
    try {
      await apiRequest('post', `/payment/${selectedTenant._id}`, {
        amount: parseFloat(paymentData.amount || 0),
        pending_amount: parseFloat(paymentData.pending_amount || 0),
        initial_reading: parseFloat(paymentData.initial_reading || 0),
        current_reading: parseFloat(paymentData.current_reading || 0),
        rate_per_unit: parseFloat(paymentData.rate_per_unit || 0),
        electricity_amount: parseFloat(paymentData.electricity_amount || 0),
        date: paymentData.date.toISOString().split('T')[0],
        month: paymentData.month,
        year: parseInt(paymentData.year),
        method: paymentData.method,
        status: paymentData.status
      })
      setShowPayModal(false)
      alert(`Payment entry recorded!`)
      fetchTenants()
    } catch (error) {
      console.error('Error recording payment:', error)
    }
  }

  const viewHistory = async (tenant) => {
    try {
      const response = await apiRequest('get', `/payments/${tenant._id}`)
      setPaymentHistory(response.data)
      setSelectedTenant(tenant)
      setView('history')
    } catch (error) {
      console.error('Error fetching history:', error)
    }
  }

  const handleRecordExpense = async (e) => {
    e.preventDefault()
    try {
      const data = {
        ...expenseData,
        amount: parseFloat(expenseData.amount || 0),
        date: expenseData.date.toISOString().split('T')[0]
      }
      
      if (editingExpense) {
        await apiRequest('patch', `/expense/${editingExpense._id}`, data)
      } else {
        await apiRequest('post', '/expense', data)
      }
      
      setShowExpenseModal(false)
      setEditingExpense(null)
      setExpenseData({
        title: '', amount: '', category: 'Repair', date: new Date(), description: ''
      })
      fetchExpenses()
    } catch (error) {
      console.error('Error recording expense:', error)
      alert('Error saving expense')
    }
  }

  const handleDeleteExpense = async (id) => {
    if (!window.confirm("Are you sure you want to delete this expense?")) return
    try {
      await apiRequest('delete', `/expense/${id}`)
      fetchExpenses()
    } catch (error) {
      console.error('Error deleting expense:', error)
    }
  }

  const handleRecordMaintenance = async (e) => {
    e.preventDefault()
    try {
      if (editingMaintenance) {
        await apiRequest('patch', `/maintenance/${editingMaintenance._id}`, {
          issue: maintenanceData.issue,
          notes: maintenanceData.notes,
          priority: maintenanceData.priority,
          status: maintenanceData.status,
          cost: parseFloat(maintenanceData.cost || 0)
        })
      } else {
        await apiRequest('post', '/maintenance', {
          ...maintenanceData,
          cost: parseFloat(maintenanceData.cost || 0),
          created_at: maintenanceData.created_at.toISOString().split('T')[0]
        })
      }
      setShowMaintenanceModal(false)
      setEditingMaintenance(null)
      setMaintenanceData({
        tenant_id: '', tenant_name: '', issue: '', notes: '', priority: 'Medium', status: 'pending', cost: '', created_at: new Date()
      })
      fetchMaintenance()
    } catch (error) {
      alert(error.response?.data?.detail || 'Error saving maintenance request')
      console.error('Error recording maintenance:', error)
    }
  }

  const openMaintenanceModal = (tenant) => {
    setSelectedTenant(tenant)
    setEditingMaintenance(null)
    setMaintenanceData({
      tenant_id: tenant._id,
      tenant_name: tenant.name,
      issue: '',
      notes: '',
      priority: 'Medium',
      status: 'pending',
      cost: '',
      created_at: new Date()
    })
    setShowMaintenanceModal(true)
  }

  const openEditMaintenanceModal = (m) => {
    if (m.status === 'resolved') return; // Cannot edit resolved requests
    setEditingMaintenance(m)
    setMaintenanceData({
      tenant_id: m.tenant_id,
      tenant_name: m.tenant_name,
      issue: m.issue,
      notes: m.notes || '',
      priority: m.priority,
      status: m.status,
      cost: m.cost || '',
      created_at: new Date(m.created_at)
    })
    setShowMaintenanceModal(true)
  }

  const updateMaintenanceStatus = async (id, status) => {
    try {
      await apiRequest('patch', `/maintenance/${id}`, { status })
      fetchMaintenance()
    } catch (error) {
      alert(error.response?.data?.detail || 'Error updating status')
      console.error('Error updating status:', error)
    }
  }

  const handleRecordNote = async (e) => {
    e.preventDefault()
    try {
      if (editingNote) {
        await apiRequest('patch', `/note/${editingNote._id}`, noteData)
      } else {
        await apiRequest('post', '/note', noteData)
      }
      setShowNoteModal(false)
      setEditingNote(null)
      setNoteData({ title: '', content: '', category: 'General' })
      fetchNotes()
    } catch (error) {
      console.error('Error saving note:', error)
    }
  }

  const handleDeleteNote = async (id) => {
    if (!window.confirm("Are you sure you want to delete this note?")) return
    try {
      await apiRequest('delete', `/note/${id}`)
      fetchNotes()
    } catch (error) {
      console.error('Error deleting note:', error)
    }
  }

  const handleExportTenants = async () => {
    try {
      const params = new URLSearchParams()
      if (filterStatus !== 'All') params.append('status', filterStatus)
      if (minRent) params.append('min_rent', minRent)
      if (maxRent) params.append('max_rent', maxRent)
      if (searchQuery) params.append('search', searchQuery)

      const response = await axios.get(`${API_BASE}/tenants/export?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      })
      
      const blobURL = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = blobURL
      link.setAttribute('download', `rentals_export_${new Date().toISOString().split('T')[0]}.csv`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Error exporting data:', error)
      alert("Error exporting data")
    }
  }

  const handleExportTenantPDF = async (tenant) => {
    try {
      const response = await axios.get(`${API_BASE}/tenant/${tenant._id}/pdf`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      })
      
      const blobURL = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
      const link = document.createElement('a')
      link.href = blobURL
      link.setAttribute('download', `Tenant_Record_${tenant.name.replace(/\s+/g, '_')}.pdf`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Error exporting PDF:', error)
      alert("Error generating PDF")
    }
  }

  const shareOnWhatsApp = (payment, tenant) => {
    const total = (parseFloat(payment.amount || 0) + parseFloat(payment.electricity_amount || 0)).toFixed(2);
    const message = `*Rent Receipt - Housely.io*%0A` +
      `--------------------------%0A` +
      `*Tenant:* ${tenant.name}%0A` +
      `*Room:* ${tenant.room_number}%0A` +
      `*Period:* ${payment.month} ${payment.year}%0A%0A` +
      `*Rent Paid:* ₹${payment.amount}%0A` +
      `*Electricity:* ₹${payment.electricity_amount?.toFixed(2) || '0.00'}%0A` +
      `--------------------------%0A` +
      `*Total Received:* ₹${total}%0A%0A` +
      `Thank you for the payment!`;
    
    window.open(`https://wa.me/91${tenant.phone}?text=${message}`, '_blank');
  }

  const filteredTenants = tenants.filter(tenant => 
    tenant.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    tenant.room_number.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Dashboard Stats Calculations
  const activeTenantsCount = tenants.filter(t => t.status === 'active').length
  const leavingTenantsCount = tenants.filter(t => t.status === 'leaving').length
  const totalRentRevenue = tenants.reduce((acc, curr) => acc + (curr.rent_amount || 0), 0)
  const totalExpenses = expenses.reduce((acc, curr) => acc + (curr.amount || 0), 0)
  const netProfit = totalRentRevenue - totalExpenses
  
  // New Stats for KYC and Activity
  const totalDocuments = tenants.reduce((acc, curr) => acc + (curr.documents?.length || 0), 0)
  const kycCompliantCount = tenants.filter(t => t.documents?.length > 0).length
  const kycPercentage = tenants.length > 0 ? Math.round((kycCompliantCount / tenants.length) * 100) : 0

  // Derive Recent Activity
  const formatRelativeTime = (dateString) => {
    if (!dateString) return 'N/A'
    
    // If the date string doesn't have a timezone, assume it's UTC
    let utcString = dateString;
    if (dateString.includes('T') && !dateString.endsWith('Z') && !dateString.includes('+')) {
      utcString = `${dateString}Z`;
    }

    const now = new Date()
    const past = new Date(utcString)
    const diffInMs = now - past
    const diffInMins = Math.floor(diffInMs / (1000 * 60))
    const diffInHours = Math.floor(diffInMins / 60)
    const diffInDays = Math.floor(diffInHours / 24)

    if (diffInMins < 1) return 'Just now'
    if (diffInMins < 60) return `${diffInMins}m ago`
    if (diffInHours < 24) return `${diffInHours}h ago`
    if (diffInDays < 7) return `${diffInDays}d ago`
    return past.toLocaleDateString()
  }

  const recentPayments = tenants.flatMap(t => (t.payments || []).map(p => ({
    ...p, 
    tenantName: t.name, 
    type: 'payment',
    activityDate: p.updated_at || p.date // Fallback to date if updated_at is missing for old records
  })))

  const recentDocs = tenants.flatMap(t => (t.documents || []).map(d => ({
    ...d, 
    tenantName: t.name, 
    type: 'document',
    activityDate: d.upload_date
  })))

  const recentActivity = [...recentPayments, ...recentDocs]
    .sort((a, b) => new Date(b.activityDate) - new Date(a.activityDate))
    .slice(0, 30)
  const currentMonth = MONTHS[new Date().getMonth()]
  const currentYear = new Date().getFullYear()
  const defaulters = tenants.filter(tenant => {
    const hasPaidCurrent = tenant.payments?.some(p => p.month === currentMonth && p.year === currentYear && p.status === 'paid')
    return !hasPaidCurrent && tenant.status === 'active'
  })

  if (!token) {
    return (
      <div className="login-overlay">
        <div className="login-card">
          <div className="brand-header">
            <div className="logo-icon">H</div>
            <h2>Housely.io</h2>
          </div>
          <p className="welcome-text">Sign in to manage your properties</p>
          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label>Username</label>
              <input 
                type="text" 
                placeholder="Enter username" 
                value={loginData.username}
                onChange={e => setLoginData({...loginData, username: e.target.value})}
                required
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input 
                type="password" 
                placeholder="Enter password" 
                value={loginData.password}
                onChange={e => setLoginData({...loginData, password: e.target.value})}
                required
              />
            </div>
            {loginError && <p className="error-msg">{loginError}</p>}
            <button type="submit" className="btn-primary full-width">Sign In</button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className={`dashboard-container ${sidebarOpen ? 'sidebar-open' : ''}`}>
      {loading && <div className="top-loading-bar"></div>}
      
      {/* Mobile Header */}
      <div className="mobile-header">
         <button className="menu-toggle" onClick={() => setSidebarOpen(true)}>
            <Menu size={24} />
         </button>
         <div className="brand mini">
            <div className="logo-icon small">H</div>
            <span>Housely.io</span>
         </div>
      </div>

      {/* Overlay for mobile sidebar */}
      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)}></div>}

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? 'show' : ''}`}>
        <div className="brand">
          <div className="logo-icon">H</div>
          <span>Housely.io</span>
          <button className="close-sidebar" onClick={() => setSidebarOpen(false)}>
             <X size={20} />
          </button>
        </div>
        
        <nav className="nav-menu">
          <button 
            className={view === 'dashboard' ? 'active' : ''} 
            onClick={() => { setView('dashboard'); setSidebarOpen(false); }}
          >
            <LayoutDashboard size={20} /> Dashboard
          </button>
          <button 
            className={view === 'tenants' ? 'active' : ''} 
            onClick={() => { setView('tenants'); setSidebarOpen(false); }}
          >
            <Users size={20} /> My Rental Persons
          </button>
          <button 
            className={view === 'expenses' ? 'active' : ''} 
            onClick={() => { setView('expenses'); setSidebarOpen(false); }}
          >
            <Receipt size={20} /> Expense Tracker
          </button>
          <button 
            className={view === 'maintenance' ? 'active' : ''} 
            onClick={() => { setView('maintenance'); setSidebarOpen(false); }}
          >
            <Wrench size={20} /> Maintenance Logs
          </button>
          <button 
            className={view === 'notes' ? 'active' : ''} 
            onClick={() => { setView('notes'); setSidebarOpen(false); }}
          >
            <StickyNote size={20} /> Quick Notes
          </button>
        </nav>

        <div className="sidebar-footer">
          <button className="logout-btn" onClick={handleLogout}>
            <LogOut size={18} /> Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        <header className="top-bar">
          <div className="search-bar">
            <Search size={18} />
            <input 
              type="text" 
              placeholder="Search by name, room or phone..." 
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
            />
          </div>
          
          <div className="filter-controls">
            <select 
              className="mini-select"
              value={filterStatus}
              onChange={e => setFilterStatus(e.target.value)}
            >
              <option value="All">All Status</option>
              <option value="active">Active</option>
              <option value="leaving">Leaving</option>
              <option value="inactive">Inactive</option>
            </select>

            <div className="rent-filter">
              <input 
                type="number" 
                placeholder="Min Rent" 
                value={minRent}
                onChange={e => setMinRent(e.target.value)}
              />
              <span>-</span>
              <input 
                type="number" 
                placeholder="Max Rent" 
                value={maxRent}
                onChange={e => setMaxRent(e.target.value)}
              />
            </div>
          </div>

          <div className="header-actions-group">
            <button className="btn-outline" onClick={handleExportTenants}>
              <Download size={18} /> Download Data
            </button>
            <button className="btn-primary" onClick={() => setShowAddForm(true)}>
              <Plus size={18} /> Add Rental Person
            </button>
          </div>
        </header>

        {view === 'dashboard' && (
          <div className="view-content fade-in">
            <h1 className="page-title">Dashboard Overview</h1>
            
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-icon purple"><Users /></div>
                <div className="stat-data">
                  <p className="label">Total Persons</p>
                  <h3>{tenants.length}</h3>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon green"><TrendingUp /></div>
                <div className="stat-data">
                  <p className="label">Monthly Revenue</p>
                  <h3>₹{totalRentRevenue.toLocaleString()}</h3>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon blue"><ShieldCheck /></div>
                <div className="stat-data">
                  <p className="label">KYC Progress</p>
                  <h3>{kycPercentage}% ({kycCompliantCount}/{tenants.length})</h3>
                </div>
              </div>
              <div className="stat-card">
                <div className="stat-icon orange"><Receipt /></div>
                <div className="stat-data">
                  <p className="label">Net Profit (Est.)</p>
                  <h3 className={netProfit >= 0 ? 'success-text' : 'danger-text'}>₹{netProfit.toLocaleString()}</h3>
                </div>
              </div>
            </div>

            <div className="dashboard-row-grid three-col">
              <div className="content-section col-span-2">
                <div className="section-header">
                  <h2>Real-time Occupancy</h2>
                  <button className="text-btn" onClick={() => setView('tenants')}>Manage All</button>
                </div>
                <div className="table-container">
                  <table className="modern-table">
                    <thead>
                      <tr>
                        <th>Rental Person</th>
                        <th>Room</th>
                        <th>KYC</th>
                        <th>Rent (₹)</th>
                        <th>Status</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredTenants.map(tenant => {
                        const docsCount = tenant.documents?.length || 0;
                        return (
                          <tr key={tenant._id}>
                            <td>
                              <div className="name-cell">
                                <strong>{tenant.name}</strong>
                                <p>{tenant.phone}</p>
                              </div>
                            </td>
                            <td><span className="room-tag">{tenant.room_number}</span></td>
                            <td>
                               <span className={`doc-tag ${docsCount > 0 ? 'active' : 'pending'}`}>
                                 {docsCount > 0 ? <CheckCircle2 size={12}/> : <AlertCircle size={12}/>} 
                                 {docsCount} Doc
                               </span>
                            </td>
                            <td>{tenant.rent_amount?.toLocaleString()}</td>
                            <td>
                              <span className={`status-badge ${tenant.status}`}>
                                {tenant.status}
                              </span>
                            </td>
                            <td>
                              <div className="row-actions">
                                <button className="icon-btn" title="Record Payment" onClick={() => openPayModal(tenant)}><CreditCard size={16}/></button>
                                <button className="icon-btn" title="Payment History" onClick={() => viewHistory(tenant)}><History size={16}/></button>
                                <button className="icon-btn blue" title="KYC Documents" onClick={() => openDocumentModal(tenant)}><FileText size={16}/></button>
                                <button className="icon-btn orange" title="Maintenance" onClick={() => openMaintenanceModal(tenant)}><Wrench size={16}/></button>
                              </div>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="activity-section">
                <div className="section-header">
                  <h2>Recent Activity</h2>
                </div>
                <div className="activity-list">
                  {recentActivity.map((act, idx) => (
                    <div key={idx} className="activity-item">
                      <div className={`activity-icon ${act.type}`}>
                        {act.type === 'payment' ? <Wallet size={16}/> : <FileText size={16}/>}
                      </div>
                      <div className="activity-data">
                        <p><strong>{act.tenantName}</strong> {act.type === 'payment' ? `paid ₹${act.amount}` : `uploaded ${act.name}`}</p>
                        <span>{formatRelativeTime(act.activityDate)}</span>
                      </div>
                    </div>
                  ))}
                  {recentActivity.length === 0 && <p className="empty-msg">No recent activity.</p>}
                </div>

                <div className="section-header" style={{marginTop: '2rem'}}>
                  <h2 className="warning-text"><AlertTriangle size={18}/> Pending Rent</h2>
                </div>
                <div className="defaulters-list mini">
                  {defaulters.slice(0, 3).map(t => (
                    <div key={t._id} className="defaulter-card compact">
                      <div className="def-info">
                        <strong>{t.name}</strong>
                        <p>Room: {t.room_number}</p>
                      </div>
                      <button className="btn-primary mini" onClick={() => openPayModal(t)}>Pay</button>
                    </div>
                  ))}
                  {defaulters.length === 0 && <p className="empty-msg">No defaulters.</p>}
                </div>
              </div>
            </div>
          </div>
        )}

        {view === 'expenses' && (
          <div className="view-content fade-in">
            <div className="section-header">
              <h1 className="page-title">Expense Management</h1>
              <button className="btn-primary" onClick={() => {
                setEditingExpense(null);
                setExpenseData({ title: '', amount: '', category: 'Repair', date: new Date(), description: '' });
                setShowExpenseModal(true);
              }}><Plus size={18}/> Add Expense</button>
            </div>
            <div className="table-container">
              <table className="modern-table">
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Category</th>
                    <th>Date</th>
                    <th>Amount (₹)</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {expenses.map(exp => (
                    <tr key={exp._id}>
                      <td>{exp.title}</td>
                      <td><span className="category-tag">{exp.category}</span></td>
                      <td>{exp.date}</td>
                      <td className="warning-text">₹{exp.amount}</td>
                      <td>
                        <div className="row-actions">
                          <button className="icon-btn-small" onClick={() => {
                            setEditingExpense(exp);
                            setExpenseData({
                              title: exp.title,
                              amount: exp.amount,
                              category: exp.category,
                              date: new Date(exp.date),
                              description: exp.description || ''
                            });
                            setShowExpenseModal(true);
                          }}><Edit2 size={14}/></button>
                          <button className="icon-btn-small danger" onClick={() => handleDeleteExpense(exp._id)}><Trash2 size={14}/></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {expenses.length === 0 && <tr><td colSpan="5" className="empty-msg">No expenses recorded yet.</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {view === 'maintenance' && (
          <div className="view-content fade-in">
            <div className="section-header">
              <h1 className="page-title">Maintenance Logs</h1>
              <button className="btn-primary" onClick={() => {
                setSelectedTenant(null);
                setEditingMaintenance(null);
                setMaintenanceData({
                  tenant_id: '',
                  tenant_name: '',
                  issue: '',
                  notes: '',
                  priority: 'Medium',
                  status: 'pending',
                  created_at: new Date()
                });
                setShowMaintenanceModal(true);
              }}>
                <Plus size={18} /> Log New Issue
              </button>
            </div>
            <div className="maintenance-grid">
              {maintenance.map(m => (
                <div key={m._id} className={`maintenance-card ${m.status}`}>
                  <div className="m-header">
                    <span className={`priority-badge ${m.priority}`}>{m.priority}</span>
                    <span className="m-date">{m.created_at}</span>
                  </div>
                  <h3>{m.issue}</h3>
                  <div className="m-details">
                    <p>Tenant: <strong>{m.tenant_name}</strong></p>
                    {m.cost > 0 && <p className="success-text"><strong>Cost:</strong> ₹{m.cost}</p>}
                  </div>
                  {m.notes && <p className="m-notes"><strong>Note:</strong> {m.notes}</p>}
                  <div className="m-footer">
                     <span className={`status-badge ${m.status}`}>{m.status}</span>
                     <div className="card-actions-small">
                       {m.status !== 'resolved' ? (
                         <>
                           <button className="text-btn primary" onClick={() => openEditMaintenanceModal(m)}>Edit</button>
                           <button className="text-btn success" onClick={() => updateMaintenanceStatus(m._id, 'resolved')}>Mark Fixed</button>
                         </>
                       ) : (
                         <span className="fixed-label">Fixed</span>
                       )}
                     </div>
                  </div>
                </div>
              ))}
              {maintenance.length === 0 && <div className="empty-msg full-width">No maintenance requests logged.</div>}
            </div>
          </div>
        )}

        {view === 'notes' && (
          <div className="view-content fade-in">
            <div className="section-header">
              <h1 className="page-title">Quick Notes</h1>
              <button className="btn-primary" onClick={() => {
                setEditingNote(null);
                setNoteData({ title: '', content: '', category: 'General' });
                setShowNoteModal(true);
              }}>
                <Plus size={18}/> New Note
              </button>
            </div>

            <div className="category-tabs">
              {['All', 'General', 'Urgent', 'Private', 'Task'].map(cat => (
                <button 
                  key={cat} 
                  className={`tab-btn ${activeNoteCategory === cat ? 'active' : ''}`}
                  onClick={() => setActiveNoteCategory(cat)}
                >
                  {cat}
                </button>
              ))}
            </div>

            <div className="notes-grid">
              {notes.filter(n => activeNoteCategory === 'All' || n.category === activeNoteCategory).map(note => (
                <div key={note._id} className={`note-card cat-${note.category.toLowerCase()}`}>
                  <div className="note-header">
                    <span className="note-category">{note.category}</span>
                    <div className="note-actions">
                      <button className="icon-btn-small" onClick={() => {
                        setEditingNote(note);
                        setNoteData({ title: note.title, content: note.content, category: note.category });
                        setShowNoteModal(true);
                      }}><Edit2 size={14}/></button>
                      <button className="icon-btn-small danger" onClick={() => handleDeleteNote(note._id)}><Trash2 size={14}/></button>
                    </div>
                  </div>
                  <h3>{note.title}</h3>
                  <p>{note.content}</p>
                  <div className="note-footer">
                    <span>{new Date(note.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
              {notes.length === 0 && <p className="empty-msg full-width">No notes found. Create your first note!</p>}
            </div>
          </div>
        )}

        {view === 'tenants' && (
          <div className="view-content fade-in">
            <h1 className="page-title">Rental Person Management</h1>
            <div className="tenant-grid">
              {filteredTenants.map(tenant => (
                <div key={tenant._id} className={`modern-tenant-card ${tenant.status}`}>
                  <div className="card-header">
                    <div className="tenant-avatar">{tenant.name.charAt(0)}</div>
                    <div className="status-dot"></div>
                  </div>
                  <h3>{tenant.name}</h3>
                  <div className="details">
                    <p><span>Room:</span> {tenant.room_number}</p>
                    <p><span>Monthly Rent:</span> ₹{tenant.rent_amount}</p>
                    <p><span>Phone:</span> {tenant.phone}</p>
                    <p><span>Joined:</span> {tenant.move_in_date}</p>
                    {tenant.status === 'leaving' && (
                      <p className="leaving-text"><span>Move Out:</span> {tenant.move_out_date}</p>
                    )}
                  </div>
                  <div className="card-actions">
                    <button className="btn-outline" onClick={() => openPayModal(tenant)}>
                      <CreditCard size={16} /> Pay
                    </button>
                    <button className="btn-outline" onClick={() => viewHistory(tenant)}>
                      <History size={16} /> History
                    </button>
                    <button className="btn-outline purple-text" onClick={() => {
                      setSelectedTenant(tenant);
                      setView('full-record');
                    }}>
                      <UserCheck size={16} /> Full Record
                    </button>
                    <button className="btn-outline blue-text" onClick={() => openDocumentModal(tenant)}>
                      <FileText size={16} /> KYC
                    </button>
                    <button className="btn-outline orange-text" onClick={() => openMaintenanceModal(tenant)}>
                      <Wrench size={16} /> Fix
                    </button>
                  </div>
                </div>
              ))}
              {filteredTenants.length === 0 && (
                <div className="empty-msg full-width">No rental persons found matching your search.</div>
              )}
            </div>
          </div>
        )}

        {view === 'full-record' && (
          <div className="view-content fade-in">
            <button className="back-link" onClick={() => setView('tenants')}>← Back to Rental Persons</button>
            <div className="section-header">
              <h1 className="page-title">Tenant Full Record: {selectedTenant?.name}</h1>
              <div className="header-actions">
                 <button className="btn-primary" onClick={() => handleExportTenantPDF(selectedTenant)}>
                    <FileText size={18} /> Download PDF Record
                 </button>
                 <span className={`status-badge ${selectedTenant?.status}`}>{selectedTenant?.status}</span>
              </div>
            </div>

            <div className="record-grid">
              <div className="record-main-card">
                 <div className="record-section">
                    <h3><UserCheck size={18}/> Personal & Room Details</h3>
                    <div className="details-list">
                      <div className="detail-row"><span>Phone:</span> <strong>{selectedTenant?.phone}</strong></div>
                      <div className="detail-row"><span>Room Number:</span> <strong>{selectedTenant?.room_number}</strong></div>
                      <div className="detail-row"><span>Aadhar/ID:</span> <strong>{selectedTenant?.aadhar_number || 'Not Provided'}</strong></div>
                      <div className="detail-row"><span>Emergency:</span> <strong>{selectedTenant?.emergency_contact || 'Not Provided'}</strong></div>
                      <div className="detail-row"><span>Monthly Rent:</span> <strong>₹{selectedTenant?.rent_amount}</strong></div>
                      <div className="detail-row"><span>Move-in Date:</span> <strong>{selectedTenant?.move_in_date}</strong></div>
                    </div>
                 </div>

                 <div className="record-section">
                    <h3><FileText size={18}/> KYC Documents ({selectedTenant?.documents?.length || 0})</h3>
                    <div className="record-docs">
                       {selectedTenant?.documents?.map(doc => (
                         <div key={doc._id} className="mini-doc-item">
                           <FileText size={14}/>
                           <span>{doc.name} ({doc.type})</span>
                           <a href={doc.file_path} target="_blank" rel="noreferrer">View</a>
                         </div>
                       ))}
                       {(!selectedTenant?.documents || selectedTenant.documents.length === 0) && <p className="empty-mini">No documents found.</p>}
                    </div>
                 </div>
              </div>

              <div className="record-side-column">
                 <div className="record-section">
                    <h3><History size={18}/> Payment Summary</h3>
                    <div className="payment-summary-stats">
                       <div className="summary-stat">
                          <p>Total Paid</p>
                          <h4 className="success-text">₹{selectedTenant?.payments?.reduce((acc, p) => acc + (p.amount || 0), 0).toLocaleString()}</h4>
                       </div>
                       <div className="summary-stat">
                          <p>Last Payment</p>
                          <h4>{selectedTenant?.payments?.length > 0 ? selectedTenant.payments[selectedTenant.payments.length-1].date : 'None'}</h4>
                       </div>
                    </div>
                 </div>

                 <div className="record-section">
                    <h3><CreditCard size={18}/> Recent Payments</h3>
                    <div className="mini-history-list">
                       {selectedTenant?.payments?.slice().reverse().slice(0, 5).map(p => (
                         <div key={p._id} className="mini-history-item">
                           <div className="mh-info">
                              <strong>{p.month} {p.year}</strong>
                              <span>{p.date}</span>
                           </div>
                           <div className="mh-amount success-text">₹{p.amount}</div>
                         </div>
                       ))}
                    </div>
                 </div>
              </div>
            </div>
          </div>
        )}

        {view === 'history' && (
          <div className="view-content fade-in">
            <button className="back-link" onClick={() => setView('dashboard')}>← Back to Dashboard</button>
            <div className="section-header">
              <h1 className="page-title">Payment History: {selectedTenant?.name}</h1>
              <span className="room-tag">Room {selectedTenant?.room_number}</span>
            </div>

            {/* Desktop Table View */}
            <div className="table-container desktop-only">
              <table className="modern-table">
                <thead>
                  <tr>
                    <th>For Period</th>
                    <th>Payment Date</th>
                    <th>Submitted (Rent)</th>
                    <th>Electricity Bill</th>
                    <th>Status</th>
                    <th>Method</th>
                    <th>Receipt</th>
                  </tr>
                </thead>
                <tbody>
                  {paymentHistory.sort((a,b) => new Date(b.date) - new Date(a.date)).map(payment => (
                    <tr key={payment._id}>
                      <td><span className="period-badge">{payment.month} {payment.year}</span></td>
                      <td>{payment.date}</td>
                      <td className="success-text">₹{payment.amount}</td>
                      <td>
                        <div className="electricity-cell">
                          <strong>₹{payment.electricity_amount?.toFixed(2) || '0.00'}</strong>
                          {payment.current_reading > 0 && (
                            <p className="reading-text">({payment.initial_reading} → {payment.current_reading})</p>
                          )}
                        </div>
                      </td>
                      <td>
                        <span className={`status-badge ${payment.status}`}>
                          {payment.status}
                        </span>
                      </td>
                      <td><span className="method-badge">{payment.method || 'Cash'}</span></td>
                      <td>
                         <button className="icon-btn success" onClick={() => shareOnWhatsApp(payment, selectedTenant)}>
                           <Share2 size={16}/> Receipt
                         </button>
                      </td>
                    </tr>
                  ))}
                  {paymentHistory.length === 0 && (
                    <tr><td colSpan="7" className="empty-msg">No payments recorded for this rental person.</td></tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Mobile Card View */}
            <div className="mobile-only history-cards">
              {paymentHistory.sort((a,b) => new Date(b.date) - new Date(a.date)).map(payment => (
                <div key={payment._id} className="history-mobile-card">
                  <div className="hm-header">
                    <span className="period-badge">{payment.month} {payment.year}</span>
                    <span className={`status-badge ${payment.status}`}>{payment.status}</span>
                  </div>
                  <div className="hm-body">
                    <div className="hm-row">
                      <span>Date:</span>
                      <strong>{payment.date}</strong>
                    </div>
                    <div className="hm-row">
                      <span>Rent Paid:</span>
                      <strong className="success-text">₹{payment.amount}</strong>
                    </div>
                    <div className="hm-row">
                      <span>Electricity:</span>
                      <strong>₹{payment.electricity_amount?.toFixed(2) || '0.00'}</strong>
                    </div>
                    {payment.current_reading > 0 && (
                      <div className="hm-row readings">
                        <span>Readings:</span>
                        <p>{payment.initial_reading} → {payment.current_reading}</p>
                      </div>
                    )}
                    <div className="hm-row">
                      <span>Method:</span>
                      <span className="method-badge">{payment.method || 'Cash'}</span>
                    </div>
                  </div>
                  <div className="hm-footer">
                    <button className="btn-primary full-width" onClick={() => shareOnWhatsApp(payment, selectedTenant)}>
                      <Share2 size={16}/> Share Receipt
                    </button>
                  </div>
                </div>
              ))}
              {paymentHistory.length === 0 && (
                <div className="empty-msg">No payments recorded.</div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Modal Overlay for Add Rental Person */}
      {showAddForm && (
        <div className="modal-overlay">
          <div className="modal-card scrollable">
            <div className="modal-header">
              <h2>Add New Rental Person</h2>
              <button className="close-btn" onClick={() => setShowAddForm(false)}><X size={20}/></button>
            </div>
            <form onSubmit={handleAddTenant}>
              <div className="form-group">
                <label>Full Name</label>
                <input 
                  required
                  placeholder="e.g. Rahul Sharma" 
                  value={newTenant.name}
                  onChange={e => setNewTenant({...newTenant, name: e.target.value})}
                />
              </div>
              <div className="form-grid">
                <div className="form-group">
                  <label>Phone Number</label>
                  <input 
                    required
                    type="tel"
                    maxLength="10"
                    pattern="[0-9]{10}"
                    placeholder="10-digit number" 
                    value={newTenant.phone}
                    onChange={e => {
                      const value = e.target.value.replace(/\D/g, '');
                      setNewTenant({...newTenant, phone: value})
                    }}
                  />
                </div>
                <div className="form-group">
                  <label>Room / Flat Number</label>
                  <input 
                    required
                    placeholder="e.g. A-102" 
                    value={newTenant.room_number}
                    onChange={e => setNewTenant({...newTenant, room_number: e.target.value})}
                  />
                </div>
              </div>
              <div className="form-grid">
                <div className="form-group">
                  <label>Monthly Rent (₹)</label>
                  <input 
                    required
                    type="number"
                    placeholder="e.g. 15000" 
                    value={newTenant.rent_amount}
                    onChange={e => setNewTenant({...newTenant, rent_amount: e.target.value})}
                  />
                </div>
                <div className="form-group">
                  <label>Aadhar / ID Number</label>
                  <input 
                    placeholder="12 or 16-digit Aadhar" 
                    maxLength="16"
                    pattern="\d{12}|\d{16}"
                    value={newTenant.aadhar_number}
                    onChange={e => {
                      const value = e.target.value.replace(/\D/g, '');
                      setNewTenant({...newTenant, aadhar_number: value})
                    }}
                  />
                </div>
              </div>
              <div className="form-grid">
                <div className="form-group">
                  <label>Emergency Contact</label>
                  <input 
                    placeholder="10-digit number" 
                    maxLength="10"
                    pattern="[0-9]{10}"
                    value={newTenant.emergency_contact}
                    onChange={e => {
                      const value = e.target.value.replace(/\D/g, '');
                      setNewTenant({...newTenant, emergency_contact: value})
                    }}
                  />
                </div>
                <div className="form-group">
                  <label>Move In Date</label>
                  <div className="date-input-wrapper">
                    <CalendarIcon className="input-icon" size={16} />
                    <DatePicker
                      selected={newTenant.move_in_date}
                      onChange={(date) => setNewTenant({...newTenant, move_in_date: date})}
                      className="premium-date-picker"
                      dateFormat="yyyy-MM-dd"
                      showMonthDropdown
                      showYearDropdown
                      dropdownMode="scroll"
                    />
                  </div>
                </div>
              </div>
              <div className="modal-actions">
                <button type="submit" className="btn-primary full-width">Create Rental Person</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Expense Modal */}
      {showExpenseModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h2>{editingExpense ? 'Edit Property Expense' : 'Add Property Expense'}</h2>
              <button className="close-btn" onClick={() => {
                setShowExpenseModal(false);
                setEditingExpense(null);
                setExpenseData({ title: '', amount: '', category: 'Repair', date: new Date(), description: '' });
              }}><X size={20}/></button>
            </div>
            <form onSubmit={handleRecordExpense}>
              <div className="form-group">
                <label>Title</label>
                <input required placeholder="e.g. Plumbing Repair" value={expenseData.title} onChange={e => setEditingExpense ? setExpenseData({...expenseData, title: e.target.value}) : setExpenseData({...expenseData, title: e.target.value})} />
              </div>
              <div className="form-grid">
                <div className="form-group">
                  <label>Amount (₹)</label>
                  <input required type="number" value={expenseData.amount} onChange={e => setExpenseData({...expenseData, amount: e.target.value})} />
                </div>
                <div className="form-group">
                  <label>Category</label>
                  <select className="custom-select" value={expenseData.category} onChange={e => setExpenseData({...expenseData, category: e.target.value})}>
                    <option>Repair</option>
                    <option>Cleaning</option>
                    <option>Tax</option>
                    <option>Utility Bill</option>
                    <option>Other</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label>Date</label>
                <DatePicker selected={expenseData.date} onChange={d => setExpenseData({...expenseData, date: d})} className="custom-select" />
              </div>
              <button type="submit" className="btn-primary full-width">{editingExpense ? 'Update Expense' : 'Save Expense'}</button>
            </form>
          </div>
        </div>
      )}

      {/* Maintenance Request Modal */}
      {showMaintenanceModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h2>{editingMaintenance ? 'Edit Maintenance Request' : 'Log Maintenance Request'}</h2>
              <button className="close-btn" onClick={() => {
                setShowMaintenanceModal(false);
                setEditingMaintenance(null);
                setMaintenanceData({
                  tenant_id: '', tenant_name: '', issue: '', notes: '', priority: 'Medium', status: 'pending', created_at: new Date()
                });
              }}><X size={20}/></button>
            </div>
            <p className="modal-subtitle">Reporting issue for <strong>{maintenanceData.tenant_name || '...'}</strong></p>
            <form onSubmit={handleRecordMaintenance}>
              {!editingMaintenance && !selectedTenant && (
                <div className="form-group">
                  <label>Select Rental Person</label>
                  <select 
                    required
                    className="custom-select"
                    value={maintenanceData.tenant_id}
                    onChange={e => {
                      const t = tenants.find(ten => ten._id === e.target.value);
                      setMaintenanceData({
                        ...maintenanceData, 
                        tenant_id: e.target.value, 
                        tenant_name: t ? t.name : ''
                      });
                    }}
                  >
                    <option value="">-- Choose Person --</option>
                    {tenants.map(t => (
                      <option key={t._id} value={t._id}>{t.name} (Room {t.room_number})</option>
                    ))}
                  </select>
                </div>
              )}
              <div className="form-group">
                <label>Problem / Issue Description</label>
                <textarea 
                  required 
                  className="custom-textarea"
                  placeholder="e.g. Water leakage in bathroom tap"
                  value={maintenanceData.issue}
                  onChange={e => setMaintenanceData({...maintenanceData, issue: e.target.value})}
                ></textarea>
              </div>
              <div className="form-group">
                <label>Fixing Cost (₹) - Optional</label>
                <input 
                  type="number"
                  placeholder="0"
                  className="custom-select"
                  value={maintenanceData.cost}
                  onChange={e => setMaintenanceData({...maintenanceData, cost: e.target.value})}
                />
              </div>
              <div className="form-group">
                <label>Additional Notes (for future reference)</label>
                <textarea 
                  className="custom-textarea"
                  placeholder="e.g. Needs plumber from sector 5"
                  value={maintenanceData.notes}
                  onChange={e => setMaintenanceData({...maintenanceData, notes: e.target.value})}
                ></textarea>
              </div>
              <div className="form-group">
                <label>Priority</label>
                <select className="custom-select" value={maintenanceData.priority} onChange={e => setMaintenanceData({...maintenanceData, priority: e.target.value})}>
                  <option>Low</option>
                  <option>Medium</option>
                  <option>High</option>
                </select>
              </div>
              <button type="submit" className="btn-primary full-width">{editingMaintenance ? 'Update Request' : 'Submit Request'}</button>
            </form>
          </div>
        </div>
      )}

      {/* Record Payment Modal */}
      {showPayModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h2>Record Payment</h2>
              <button className="close-btn" onClick={() => setShowPayModal(false)}><X size={20}/></button>
            </div>
            <p className="modal-subtitle">Recording for <strong>{selectedTenant?.name}</strong> (Rent: ₹{selectedTenant?.rent_amount})</p>
            <form onSubmit={handleRecordPayment}>
              <div className="form-grid">
                <div className="form-group">
                  <label>Month</label>
                  <select 
                    value={paymentData.month}
                    onChange={e => setPaymentData({...paymentData, month: e.target.value})}
                    className="custom-select"
                  >
                    {MONTHS.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Year</label>
                  <select 
                    value={paymentData.year}
                    onChange={e => setPaymentData({...paymentData, year: e.target.value})}
                    className="custom-select"
                  >
                    {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
                  </select>
                </div>
              </div>
              
              <div className="form-group">
                <label>Status</label>
                <div className="status-toggle-grid">
                  <button 
                    type="button" 
                    className={`toggle-btn ${paymentData.status === 'paid' ? 'active success' : ''}`}
                    onClick={() => setPaymentData({...paymentData, status: 'paid', pending_amount: 0})}
                  >
                    <CheckCircle2 size={16}/> Fully Paid
                  </button>
                  <button 
                    type="button" 
                    className={`toggle-btn ${paymentData.status === 'pending' ? 'active warning' : ''}`}
                    onClick={() => setPaymentData({...paymentData, status: 'pending'})}
                  >
                    <Clock size={16}/> Pending / Partial
                  </button>
                </div>
              </div>

              <div className="form-grid">
                <div className="form-group">
                  <label>Amount Submitted (₹)</label>
                  <input 
                    required
                    type="number"
                    placeholder="0"
                    value={paymentData.amount}
                    onChange={e => setPaymentData({...paymentData, amount: e.target.value})}
                  />
                </div>
              <div className="form-group">
                <label>Still Pending (₹)</label>
                <input 
                  type="number"
                  disabled={paymentData.status === 'paid'}
                  placeholder="0"
                  value={paymentData.pending_amount}
                  onChange={e => setPaymentData({...paymentData, pending_amount: e.target.value})}
                />
              </div>
            </div>

            <div className="electricity-section">
              <h4 className="section-subtitle"><TrendingUp size={16}/> Electricity Readings (Optional)</h4>
              <div className="form-grid">
                <div className="form-group">
                  <label>Initial Reading</label>
                  <input 
                    type="number"
                    placeholder="e.g. 1200"
                    value={paymentData.initial_reading}
                    onChange={e => {
                      const initial = parseFloat(e.target.value || 0);
                      const current = parseFloat(paymentData.current_reading || 0);
                      const rate = parseFloat(paymentData.rate_per_unit || 0);
                      const amount = Math.max(0, (current - initial) * rate);
                      setPaymentData({...paymentData, initial_reading: e.target.value, electricity_amount: amount})
                    }}
                  />
                </div>
                <div className="form-group">
                  <label>Current Reading</label>
                  <input 
                    type="number"
                    placeholder="e.g. 1350"
                    value={paymentData.current_reading}
                    onChange={e => {
                      const current = parseFloat(e.target.value || 0);
                      const initial = parseFloat(paymentData.initial_reading || 0);
                      const rate = parseFloat(paymentData.rate_per_unit || 0);
                      const amount = Math.max(0, (current - initial) * rate);
                      setPaymentData({...paymentData, current_reading: e.target.value, electricity_amount: amount})
                    }}
                  />
                </div>
              </div>
              <div className="form-grid">
                <div className="form-group">
                  <label>Rate per Unit (₹)</label>
                  <input 
                    type="number"
                    value={paymentData.rate_per_unit}
                    onChange={e => {
                      const rate = parseFloat(e.target.value || 0);
                      const current = parseFloat(paymentData.current_reading || 0);
                      const initial = parseFloat(paymentData.initial_reading || 0);
                      const amount = Math.max(0, (current - initial) * rate);
                      setPaymentData({...paymentData, rate_per_unit: e.target.value, electricity_amount: amount})
                    }}
                  />
                </div>
                <div className="form-group">
                  <label>Electricity Bill (Auto)</label>
                  <div className="readonly-value">₹{paymentData.electricity_amount.toFixed(2)}</div>
                </div>
              </div>
            </div>

            <div className="form-grid">
                <div className="form-group">
                  <label>Payment Method</label>
                  <select 
                    value={paymentData.method}
                    onChange={e => setPaymentData({...paymentData, method: e.target.value})}
                    className="custom-select"
                  >
                    <option value="Cash">Cash</option>
                    <option value="Online">Online</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Date Received</label>
                  <div className="date-input-wrapper">
                    <CalendarIcon className="input-icon" size={16} />
                    <DatePicker
                      selected={paymentData.date}
                      onChange={(date) => setPaymentData({...paymentData, date: date})}
                      className="premium-date-picker"
                      dateFormat="yyyy-MM-dd"
                      showMonthDropdown
                      showYearDropdown
                      dropdownMode="scroll"
                    />
                  </div>
                </div>
              </div>
              <div className="modal-actions">
                <button type="submit" className="btn-primary full-width">Save Payment Record</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Note Modal */}
      {showNoteModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h2>{editingNote ? 'Edit Note' : 'Create Quick Note'}</h2>
              <button className="close-btn" onClick={() => setShowNoteModal(false)}><X size={20}/></button>
            </div>
            <form onSubmit={handleRecordNote}>
              <div className="form-group">
                <label>Note Title</label>
                <input 
                  required 
                  placeholder="e.g. Electricity Bill Reminder" 
                  value={noteData.title}
                  onChange={e => setNoteData({...noteData, title: e.target.value})}
                />
              </div>
              <div className="form-group">
                <label>Category</label>
                <select 
                  className="custom-select"
                  value={noteData.category}
                  onChange={e => setNoteData({...noteData, category: e.target.value})}
                >
                  <option value="General">General</option>
                  <option value="Urgent">Urgent</option>
                  <option value="Private">Private</option>
                  <option value="Task">Task</option>
                </select>
              </div>
              <div className="form-group">
                <label>Write anything here...</label>
                <textarea 
                  required 
                  className="custom-textarea"
                  style={{minHeight: '200px'}}
                  placeholder="Type your notes or reminders here..."
                  value={noteData.content}
                  onChange={e => setNoteData({...noteData, content: e.target.value})}
                ></textarea>
              </div>
              <button type="submit" className="btn-primary full-width">{editingNote ? 'Update Note' : 'Save Note'}</button>
            </form>
          </div>
        </div>
      )}

      {/* Set Leaving Status Modal */}
      {showLeavingModal && (
        <div className="modal-overlay">
          <div className="modal-card">
            <div className="modal-header">
              <h2>Set Leaving Status</h2>
              <button className="close-btn" onClick={() => setShowLeavingModal(false)}><X size={20}/></button>
            </div>
            <p className="modal-subtitle">Marking <strong>{selectedTenant?.name}</strong> as leaving</p>
            <form onSubmit={handleConfirmLeaving}>
              <div className="form-group">
                <label>Expected Move Out Date</label>
                <div className="date-input-wrapper">
                  <CalendarIcon className="input-icon" size={16} />
                  <DatePicker
                    selected={leavingDate}
                    onChange={(date) => setLeavingDate(date)}
                    className="premium-date-picker"
                    dateFormat="yyyy-MM-dd"
                    showMonthDropdown
                    showYearDropdown
                    dropdownMode="scroll"
                  />
                </div>
              </div>
              <div className="modal-actions">
                <button type="submit" className="btn-primary full-width">Confirm Status Change</button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* KYC Documents Modal */}
      {showDocumentModal && (
        <div className="modal-overlay">
          <div className="modal-card scrollable">
            <div className="modal-header">
              <h2>KYC Documents</h2>
              <button className="close-btn" onClick={() => setShowDocumentModal(false)}><X size={20}/></button>
            </div>
            <p className="modal-subtitle">Managing documents for <strong>{selectedTenant?.name}</strong></p>
            
            <form onSubmit={handleUploadDocument} className="upload-form">
              <div className="form-grid">
                <div className="form-group">
                  <label>Document Name</label>
                  <input 
                    required 
                    placeholder="e.g. Front Aadhar" 
                    value={documentData.name}
                    onChange={e => setDocumentData({...documentData, name: e.target.value})}
                  />
                </div>
                <div className="form-group">
                  <label>Type</label>
                  <select 
                    className="custom-select"
                    value={documentData.type}
                    onChange={e => setDocumentData({...documentData, type: e.target.value})}
                  >
                    <option value="Aadhar">Aadhar Card</option>
                    <option value="PAN">PAN Card</option>
                    <option value="Agreement">Rent Agreement</option>
                    <option value="Other">Other ID</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label>Select File</label>
                <input 
                  type="file" 
                  className="custom-file-input"
                  onChange={e => setDocumentData({...documentData, file: e.target.files[0]})}
                />
              </div>
              <button type="submit" className="btn-primary full-width">Upload Document</button>
            </form>

            <div className="documents-list">
              <h3>Stored Documents</h3>
              {tenantDocuments.length === 0 ? (
                <p className="empty-msg">No documents uploaded yet.</p>
              ) : (
                <div className="doc-grid">
                  {tenantDocuments.map(doc => (
                    <div key={doc._id} className="doc-item">
                      <div className="doc-info">
                        <div className="doc-icon"><FileText size={20}/></div>
                        <div className="doc-details">
                          <strong>{doc.name}</strong>
                          <p>{doc.type} • {new Date(doc.upload_date).toLocaleDateString()}</p>
                        </div>
                      </div>
                      <div className="doc-actions">
                        <a 
                          href={doc.file_path} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="icon-btn blue"
                        >
                          <DoorOpen size={16}/> View
                        </a>
                        <button 
                          className="icon-btn danger" 
                          onClick={() => handleDeleteDocument(doc._id)}
                        >
                          <X size={16}/>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
